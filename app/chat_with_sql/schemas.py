from pydantic import BaseModel

class NPLRequest(BaseModel):
    connection_db: str
    question: str
    
class InputData(BaseModel):
    dialect: str
    schema_info: str
    question: str