import os

from fastapi import UploadFile


def _store_file(file: UploadFile, upload_dir: str) -> str:
    """"Stores the uploaded file in the specified directory."""
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file.filename