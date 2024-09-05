from enum import Enum
from pydantic import BaseModel

class Database(Enum):
    POSTGRES = "postgresql"
    MYSQL = "mysql"
        
class DatabaseConnectionRequest(BaseModel):
    username: str
    password: str
    host: str
    port: int
    database: str

def db_connection(request: DatabaseConnectionRequest, database_type: Database):
    return f"{database_type.POSTGRES.value}+psycopg2://{request.username}:{request.password}@{request.host}:{request.port}/{request.database}"