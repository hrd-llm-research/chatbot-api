import os

from fastapi import APIRouter, File, UploadFile, status
from .file_upload import _store_file
from ..chatbot.vector_store.vectorstore import upload_to_vectorstore
from fastapi.responses import JSONResponse
from fastapi import HTTPException, Depends
from app.auth.dependencies import get_current_active_user
from app.auth.schemas import User
from typing import Annotated

router = APIRouter(
    prefix="/files",
    tags={"file"}, 
)

current_dir = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(current_dir,"..","chatbot", "vector_store", "docs_resources")


from app.auth.dependencies import JWTBearer
from app.utils import get_db
from sqlalchemy.orm import Session
# @router.post("/get_current_user")
def get_current_user(db: Annotated[Session, Depends(get_db)]):
    import jwt
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHJpbmdAZW1haWwiLCJleHAiOjE3MjQ5NTYyNjB9.eGBfnUhMauHwdk9nDEXl2FTLZ5ug1XpLFtgg2GFgH_c"
    SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM = "HS256"
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    from app.auth import crud

    user = crud.get_user_email(db, email="string@email")
    print("user",user)
    return payload

@router.post("/file_upload")
def file_upload(
    file: UploadFile = File(...), 
                 
):
    
    filename = file.filename
    if not (filename.endswith(".txt") or filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Wrong file format.")

    # store the uploaded file
    file_name = _store_file(file, UPLOAD_DIR)
   
    #add to vector store
    collection_name = upload_to_vectorstore(file_name)
        
    # remove the file from the directory
    os.remove(os.path.join(UPLOAD_DIR, file_name))
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content = {
            "message": "File uploaded successfully",
            "success": True,
            "filename": {
                "file_name": file_name,
                "collection_name": collection_name
            },
        },
    )