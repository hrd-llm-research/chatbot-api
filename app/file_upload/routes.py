import os

from fastapi import APIRouter, File, UploadFile
from .file_upload import _store_file
from ..chatbot.vector_store.vectorstore import upload_to_vectorstore

router = APIRouter(
    prefix="/files",
    tags={"file"}, 
)

current_dir = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(current_dir,"..","chatbot", "vector_store", "docs_resources")


@router.post("/file_upload")
def file_upload(file: UploadFile = File(...), ):
    # store the uploaded file
    file_name = _store_file(file, UPLOAD_DIR)
    
    #add to vector store
    file_name_from_vector = upload_to_vectorstore(file_name)
        
    # remove the file from the directory
    os.remove(os.path.join(UPLOAD_DIR, file_name_from_vector))
    
    return {"file_name": file_name_from_vector}
    