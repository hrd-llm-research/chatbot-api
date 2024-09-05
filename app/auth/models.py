from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime

from .database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from langchain_community.vectorstores import PGVector
from sqlalchemy.orm import deferred
from datetime import datetime

    
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    history_messages = relationship("HistoryMessage", back_populates="user")
    chroma_db = relationship('ChromaDB', back_populates="user")

    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
        }
        
class HistoryMessage(Base):
    __tablename__ = "history_messages"    
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(UUID(as_uuid=True))
    history_message_file = Column(String)
    user = relationship("User", back_populates="history_messages")    
    
    
class ChromaDB(Base):
    __tablename__ = "chromadb"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    chroma_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    
    user = relationship('User', back_populates="chroma_db")
    