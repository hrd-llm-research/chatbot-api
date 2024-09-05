from sqlalchemy.orm import Session
from app.auth import schemas, crud
from .crud import add_user_id_to_langchain_db_collection, alter_table_langchain_collection
import os

from .file_upload import _store_file
from ..chatbot.vector_store.vectorstore import upload_to_vectorstore
from fastapi import HTTPException
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from dotenv import load_dotenv
from . import crud


load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
embedding = FastEmbedEmbeddings()

def file_upload_to_db(db: Session, file, user: schemas.User):
    try:
        UPLOAD_DIR = os.path.join(current_dir,"..","chatbot", "vector_store", "docs_resources")    
        filename = file.filename
        if not (filename.endswith(".txt") or filename.endswith(".pdf")):
            raise HTTPException(status_code=400, detail="Wrong file format.")

        # store the uploaded file
        file_name = _store_file(file, UPLOAD_DIR)
    
        #add to vector store in postgres
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
    
def upload_file_to_chroma(db, file, user, session_id):
    chroma_name = user.username+"@"+session_id+"_chroma_db"
    
    # Define directories
    UPLOAD_DIR = os.path.join(current_dir, "resources")
    persistent_dir = os.path.join(current_dir, "chroma_db", chroma_name)
    
    # store the uploaded file
    file_name = _store_file(file, UPLOAD_DIR)
    
    file_dir = os.path.join(UPLOAD_DIR, file_name)
    
    if not (file_name.endswith(".txt") or file_name.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Wrong file format.")
    
    print("Uploading file: ",file_dir)
        
    if file_name.endswith(".txt"):
        loader = TextLoader(file_dir)
    elif file_name.endswith(".pdf"):
        loader = PyPDFLoader(file_dir)
    else:
        raise HTTPException(status_code=400, detail="Wrong file format.")
    
    documents = loader.load()
                    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
    # Split the documents into smaller chunks
    chunks = text_splitter.split_documents(documents)
    
    # find if chroma existing from database
    chroma_data = crud.get_chroma_db_by_chroma_db_name(db, chroma_name, user.id)
    
    # Create an instance of the Chroma class
    chroma_instance = Chroma(collection_name="mycollection", embedding_function=embedding)
    # condition: if there chroma name already exists
    if not chroma_data:
    # insert chroma database name to database
        chroma_data = crud.create_chroma(db, user.id, chroma_name)
        
        chroma_instance.from_documents(
            documents=chunks, 
            persist_directory=persistent_dir, 
            embedding=embedding
        )
    else:
        chroma_instance.add_documents(
            documents=chunks,
            persist_directory=persistent_dir, 
            embedding=embedding
        )
    
    
    # remove the file from the directory
    os.remove(os.path.join(UPLOAD_DIR, file_name))
    
    return chroma_data
    
def get_all_chromas(db, user_id):
    return crud.get_all_chroma_db(db, user_id)

def delete_chroma_by_chroma_name(db, chroma_name,id):
    try:
        crud.delete_chroma_db_by_chroma_db_name(db, chroma_name,id)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=404, detail="Chroma not found.")