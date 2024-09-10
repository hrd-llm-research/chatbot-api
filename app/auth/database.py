from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Connect to the SQLite database
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:123@110.74.194.123:6000/chatbot_api"

Base = declarative_base()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

