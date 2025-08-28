# WebConnect

WebConnect is a simple web-based SSH client, file transfer, and file manager built with FastAPI, HTML5 and WebSockets.

## Setup

Install dependencies (you can use a mirror if needed):

```
pip install -r requirements.txt -i https://mirrors.bfsu.edu.cn/pypi/web/simple
```

## Running

Start the development server:

```
uvicorn main:app --reload
```

Open `http://localhost:8000` in your browser to access the web terminal, file upload/download forms, and the simple file manager for listing and deleting remote files.
