import asyncio
import stat
from fastapi import FastAPI, WebSocket, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import paramiko

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws/ssh")
async def websocket_ssh(websocket: WebSocket, host: str, username: str, password: str, port: int = 22):
    await websocket.accept()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username, password=password)
        channel = client.invoke_shell()

        async def send_output():
            loop = asyncio.get_event_loop()
            try:
                while True:
                    data = await loop.run_in_executor(None, channel.recv, 1024)
                    if not data:
                        break
                    await websocket.send_text(data.decode(errors="ignore"))
            except Exception:
                pass

        writer = asyncio.create_task(send_output())

        while True:
            data = await websocket.receive_text()
            channel.send(data)
    except Exception as exc:
        await websocket.send_text(f"Connection error: {exc}")
    finally:
        try:
            channel.close()
        except Exception:
            pass
        client.close()
        await websocket.close()


@app.post("/upload")
async def upload_file(
    host: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    remote_path: str = Form(...),
    file: UploadFile = File(...),
    port: int = Form(22),
):
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    data = await file.read()
    with sftp.open(remote_path, "wb") as remote:
        remote.write(data)
    sftp.close()
    transport.close()
    return {"status": "uploaded"}


@app.get("/download")
async def download_file(host: str, username: str, password: str, remote_path: str, port: int = 22):
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    remote_file = sftp.open(remote_path, "rb")

    async def file_iterator():
        while True:
            data = remote_file.read(1024)
            if not data:
                break
            yield data
        remote_file.close()
        sftp.close()
        transport.close()

    return StreamingResponse(file_iterator(), media_type="application/octet-stream")


@app.get("/list")
async def list_dir(host: str, username: str, password: str, path: str, port: int = 22):
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    items = []
    for attr in sftp.listdir_attr(path):
        items.append(
            {"filename": attr.filename, "is_dir": stat.S_ISDIR(attr.st_mode)}
        )
    sftp.close()
    transport.close()
    return {"items": items}


@app.post("/delete")
async def delete_file(
    host: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    remote_path: str = Form(...),
    port: int = Form(22),
):
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.remove(remote_path)
    sftp.close()
    transport.close()
    return {"status": "deleted"}
