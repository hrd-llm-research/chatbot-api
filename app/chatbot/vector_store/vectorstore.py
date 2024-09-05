import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders import PyPDFDirectoryLoader
from app.chatbot.vector_store.db import CONNECTION_STRING
from langchain_community.vectorstores import PGVector
from langchain_community.embeddings import FastEmbedEmbeddings
from fastapi import HTTPException

load_dotenv()

def upload_to_vectorstore(filename: str):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_dir = os.path.join(current_dir,"docs_resources", filename)
        
        COLLECTION_NAME = filename
        
        if not os.path.exists(file_dir):
            raise FileNotFoundError(f"File {filename} was not found.")

        embedding = FastEmbedEmbeddings() 
        
        if filename.endswith(".txt"):
            loader = TextLoader(file_dir)
        elif filename.endswith(".pdf"):
            loader = PyPDFLoader(file_dir)
        else:
            raise HTTPException(status_code=400, detail="Wrong file format.")
        
        documents = loader.load()
                    
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        # Split the documents into smaller chunks
        chunks = text_splitter.split_documents(documents)
                
        # Use pgvector to store all the chunks
        PGVector.from_documents(
            embedding = embedding,
            documents = chunks,
            collection_name = COLLECTION_NAME,
            connection_string = CONNECTION_STRING,
            pre_delete_collection = False  ,
            use_jsonb=True
        )
        return COLLECTION_NAME
    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))



    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_dir = os.path.join(current_dir,"docs_resources", filename)
        
        COLLECTION_NAME = filename
        
        if not os.path.exists(file_dir):
            raise FileNotFoundError(f"File {filename} was not found.")

        embedding = FastEmbedEmbeddings() 
        
        if filename.endswith(".txt"):
            loader = TextLoader(file_dir)
        elif filename.endswith(".pdf"):
            loader = PyPDFLoader(file_dir)
        else:
            raise HTTPException(status_code=400, detail="Wrong file format.")
        
        documents = loader.load()
                    
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        # Split the documents into smaller chunks
        chunks = text_splitter.split_documents(documents)
                
        # Use pgvector to store all the chunks
        PGVector.from_documents(
            embedding = embedding,
            documents = chunks,
            collection_name = COLLECTION_NAME,
            connection_string = CONNECTION_STRING,
            pre_delete_collection = False  ,
            use_jsonb=True
        )
        return COLLECTION_NAME
    except Exception as e:
        raise HTTPException(status_code=400, detail=e)