import uuid
from pydantic import BaseModel

class HistoryMessageCreate(BaseModel):
    user_id: int
    session_id: str
    history_id: str

