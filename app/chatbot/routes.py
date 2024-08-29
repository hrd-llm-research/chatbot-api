from fastapi import APIRouter
from .chain import chatbot_with_postgres, chat_with_collection, chatbot
from pydantic import BaseModel

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

@router.post("/conversation")
async def read_conversation(
        question: InvokeRequest, 
    ):
    response = chatbot_with_postgres(question.input)
    return response    

@router.post("/conversation_with_redis")
async def read_conversation(
        question: InvokeRequest, 
    ):
    response = chatbot(question.input)
    return response  

@router.post("/chat_with_collection")
async def read_chat_with_collection(
    request: CollectionRequest
):
    response = chat_with_collection(request.collection_name, request.input)
    return response