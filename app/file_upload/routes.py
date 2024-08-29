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


@router.post("/file_upload")
def file_upload(current_user: Annotated[User, Depends(get_current_active_user)] ,
    file: UploadFile = File(...), 
                 
):
    
    filename = file.filename
    if not (filename.endswith(".txt") or filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Wrong file format.")

    # store the uploaded file
    file_name = _store_file(file, UPLOAD_DIR)
   
    #add to vector store
    file_name_from_vector = upload_to_vectorstore(file_name)
        
    # remove the file from the directory
    os.remove(os.path.join(UPLOAD_DIR, file_name_from_vector))
    
    # return {"file_name": file_name_from_vector}
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content = {
            "message": "File uploaded successfully",
            "success": True,
            "filename": file_name_from_vector,
        },
    )