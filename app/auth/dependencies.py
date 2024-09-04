from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from app.utils import get_db
from app.auth import crud
from typing import Annotated
from fastapi import Depends,HTTPException, status
from app.auth.schemas import TokenData, User, UserResponse
from sqlalchemy.orm import Session
from typing import Optional

import jwt

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db, email: str, password: str):
    user = crud.get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    
    to_encode.update({"exp": expire})
    
    # Encode the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception

        token_data = TokenData(email=email)
        user = crud.get_user_by_email(db, email=token_data.email)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user

    except Exception as e:
        print(f"Invalid token: {e}")
        raise credentials_exception
    
async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    # if current_user.is_active == False:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def verify_token_access(token:str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        email: str = payload.get("email")
        token_data = TokenData(email=email) 
    except Exception as e:
        print(e)
    return token_data

def transform_user_dto(user):
    transform_user = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email
    )
    return transform_user