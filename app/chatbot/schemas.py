import uuid
from pydantic import BaseModel

class HistoryMessageCreate(BaseModel):
    user_id: int
    session_id: str
    history_message_file: str

class AIMessage(BaseModel):
    message: str
    session_id: str