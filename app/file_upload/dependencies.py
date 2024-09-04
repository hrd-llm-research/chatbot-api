from sqlalchemy.orm import Session
from app.auth import schemas, crud
from .crud import add_user_id_to_langchain_db_collection, alter_table_langchain_collection
import os

from .file_upload import _store_file
from ..chatbot.vector_store.vectorstore import upload_to_vectorstore
from fastapi import HTTPException

current_dir = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(current_dir,"..","chatbot", "vector_store", "docs_resources")

def file_upload_to_db(db: Session, file, user: schemas.User):
    try:
            
        filename = file.filename
        if not (filename.endswith(".txt") or filename.endswith(".pdf")):
            raise HTTPException(status_code=400, detail="Wrong file format.")

        # store the uploaded file
        file_name = _store_file(file, UPLOAD_DIR)
    
        #add to vector store
        collection_name = upload_to_vectorstore(file_name)

        # alter add user_id column in langchain_pg_collection table
        alter_table_langchain_collection(db)

        # add user_id to langchain_pg_collection table
        transformed_user = crud.get_user_by_email(db, user.email)
        add_user_id_to_langchain_db_collection(db, transformed_user.id, collection_name)
            
        # remove the file from the directory
        os.remove(os.path.join(UPLOAD_DIR, file_name))
        
        return {
            "file_name": file_name,
            "colection_name": collection_name
        }
    except Exception as e:
        raise e
    
