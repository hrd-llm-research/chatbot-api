from .schemas import HistoryMessageCreate
from app.auth.models import HistoryMessage
from sqlalchemy.orm import Session
import uuid

def create_history_message(db: Session, history_message: HistoryMessageCreate):
    db_history = HistoryMessage(
        user_id = history_message.user_id,
        session_id = history_message.session_id,
        history_message_file = history_message.history_message_file,
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def get_histoy_by_session_id(db: Session, session_id: uuid):
    session_id_db = db.query(HistoryMessage.session_id).filter(HistoryMessage.session_id == session_id).first()
    return session_id_db

def get_history_message_by_session_id(db: Session, session_id):
    history_db = db.query(HistoryMessage.history_message_file).filter(HistoryMessage.session_id == session_id).first()
    return history_db