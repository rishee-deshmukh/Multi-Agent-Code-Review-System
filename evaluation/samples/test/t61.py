import os

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI()
UPLOAD_DIR = "/var/app/uploads"
MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/png", "image/jpeg"}


@app.post("/avatars")
async def upload_avatar(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="unsupported type")
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as fh:
        fh.write(data)
    return {"stored_as": file.filename, "bytes": len(data)}
