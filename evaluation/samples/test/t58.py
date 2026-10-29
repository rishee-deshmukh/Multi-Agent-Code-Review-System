import os
import tarfile
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI()
UPLOAD_DIR = "/var/app/uploads"
MAX_BYTES = 5 * 1024 * 1024


@app.post("/avatars")
async def upload_avatar(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=415, detail="PNG only")
    stored = f"{uuid.uuid4().hex}.png"
    with open(os.path.join(UPLOAD_DIR, stored), "wb") as fh:
        fh.write(data)
    return {"stored_as": stored}


def import_backup(archive_path, dest):
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(archive_path) as tar:
        tar.extractall(dest, filter="data")
    return sorted(os.listdir(dest))
