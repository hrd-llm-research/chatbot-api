from fastapi import APIRouter
from .chain import chat_with_collection, chatbot_with_all_collection, chatbot
from pydantic import BaseModel
import uuid
from app.utils import get_db
from sqlalchemy.orm import Session
from fastapi import Depends, status
from . import dependencies
from fastapi.responses import JSONResponse

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

# @router.post("/conversation")
async def read_conversation(
        question: InvokeRequest, 
    ):
    response = chatbot_with_all_collection(question.input)
    return response    

# @router.post("/conversation_with_redis")
async def read_conversation(
        question: InvokeRequest, 
    ):
    response = chatbot(question.input)
    return response  

@router.post("/chat_with_collection")
async def read_chat_with_collection(
    request: CollectionRequest,
    session_id,
    db: Session = Depends(get_db)
):
    response = chat_with_collection(request.collection_name, request.input, session_id, db)
    return response

@router.post("/create_new_chat")
async def create_new_chat():
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
async def save_chat_session(session_id: str, db: Session = Depends(get_db) ):
    dependencies.save_message_to_minio(db, session_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Chat session have been saved successfully",
            "success": True,
        }
    )