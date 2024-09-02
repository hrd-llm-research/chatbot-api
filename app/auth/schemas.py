from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    
    def to_dict(self):
        return {
            "access_token": self.access_token,
            "token_type": self.token_type
        }
    
class User(BaseModel):
    username: str | None = None
    email: str | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    
    # This tells Pydantic to read the data as if it were an ORM model, 
    # allowing you to use SQLAlchemy models directly.
    class Config:
        # orm_mode = True
        from_attributes = True
        
    
class TokenData(BaseModel):
    email: str | None = None
    
class UserCreate(User):
    password: str
    
class UserInDB(User):
    password: str