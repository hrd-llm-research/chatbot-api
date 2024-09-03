import os

from fastapi import APIRouter, File, UploadFile, status
from .file_upload import _store_file
from ..chatbot.vector_store.vectorstore import upload_to_vectorstore
from fastapi.responses import JSONResponse
from fastapi import HTTPException, Depends
from app.auth.dependencies import get_current_active_user
from app.auth.schemas import User
from typing import Annotated
from app.utils import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(
    prefix="/files",
    tags={"file"}, 
)

current_dir = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(current_dir,"..","chatbot", "vector_store", "docs_resources")

@router.post("/file_upload")
def file_upload(
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...), 
    db: Session = Depends(get_db) 
):

    filename = file.filename
    if not (filename.endswith(".txt") or filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Wrong file format.")

    # store the uploaded file
    file_name = _store_file(file, UPLOAD_DIR)
   
    #add to vector store
    collection_name = upload_to_vectorstore(file_name)

    # alter user_id column in langchain_pg_collection table
    alter_table_langchain_collection(db)
    
    # insert user id into database table langchain_pg_collection
    # =====
        
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
    
def alter_table_langchain_collection(db: Session):
    try:
        column_check = db.execute(
            text("""
                SELECT attname
                FROM pg_catalog.pg_attribute
                WHERE attrelid = 'langchain_pg_collection'::regclass
                AND attname = 'user_id'
                AND NOT attisdropped;     
            """)
        ).fetchone()    

        if column_check is None:
            # If column does not exist, add it
            db.execute(text("""
                ALTER TABLE langchain_pg_collection 
                ADD COLUMN user_id INTEGER,
                ADD CONSTRAINT fk_user
                FOREIGN KEY (user_id) REFERENCES users(id)                  
            """))  
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
        