from sqlalchemy import Boolean, Column, Integer, String, ForeignKey

from .database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    history_messages = relationship("HistoryMessage", back_populates="user")
    
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
    history_id = Column(String)
    user = relationship("User", back_populates="history_messages")    