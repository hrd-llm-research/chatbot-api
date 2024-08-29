import os

from langchain_community.vectorstores import PGVector
from app.chatbot.vector_store.pgvector_service import PgvectorService
from dotenv import load_dotenv
import psycopg
    
load_dotenv()

CONNECTION_STRING = PGVector.connection_string_from_db_params(
    driver=os.environ.get("PGVECTOR_DRIVER"),
    host=os.environ.get("PGVECTOR_HOST"),
    port=os.environ.get("PGVECTOR_PORT"),
    database=os.environ.get("PGVECTOR_DATABASE"),
    user=os.environ.get("PGVECTOR_USER"),
    password=os.environ.get("PGVECTOR_PASSWORD"),
)

db_conn = PgvectorService(CONNECTION_STRING)

conn_info = "postgresql://postgres:123@localhost:5434/chatbot_api" 
sync_connection = psycopg.connect(conn_info)