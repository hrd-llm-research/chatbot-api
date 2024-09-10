from fastapi import APIRouter
from .chain import chat_with_collection, chat_with_chroma_db
from pydantic import BaseModel
import uuid
from app.utils import get_db
from sqlalchemy.orm import Session
from fastapi import Depends, status
from . import dependencies
from fastapi.responses import JSONResponse
from app.auth.schemas import User
from app.auth.dependencies import get_current_active_user, transform_user_dto
from typing import Annotated
from app.auth.crud import get_user_by_email
# from langsmith import traceable

import os

current_dir = os.path.dirname(os.path.abspath(__file__))



router = APIRouter(
    prefix="/chatbot",
    tags={"chatbot"}
)



    
class InvokeRequest(BaseModel):
    input: str
    class Config:
        arbitrary_types_allowed = True
        
class CollectionRequest(InvokeRequest):
    collection_name: str

# @router.post("/chat_with_collection")
async def read_chat_with_collection(
    request: CollectionRequest,
    session_id,
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)
    
    response = chat_with_collection(request.collection_name, request.input, session_id, db, transform_user)
    return response


@router.post("/chat_with_chroma_db")
async def read_chat_with_chroma_db(
    chroma_db_name: str,
    question: str,
    session_id,
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)

    
    response = chat_with_chroma_db(chroma_db_name, question, session_id, db, transform_user)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Chat session started with session ID: {}".format(session_id),
            "success": True,
            "payload": response,
        }
    )

# @traceable
@router.post("/create_new_chat")
async def create_new_chat(
    current_user: Annotated[User, Depends(get_current_active_user)], 
):
    session_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "New chat session started with session ID: {}".format(session_id),
            "success": True,
            "session_id": session_id,
        }
    )


""""
Save session from UI when user off focus
"""
@router.post("/save_chat_session")
async def save_chat_session(
    session_id: str, 
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: Session = Depends(get_db),
                    
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)

    dependencies.save_message_to_minio(db, session_id, transform_user, current_dir)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Chat session have been saved successfully",
            "success": True,
        }
    )
    

