from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.utils import get_db
from app.auth.dependencies import get_current_active_user, transform_user_dto
from app.auth.crud import get_user_by_email
from typing import Annotated
from app.auth.schemas import User
from .dependenies import generate_api_key

router = APIRouter(
    prefix="/api generator",
    tags=["api generator"]
)

@router.post("/create_api_key")
def create_api_key(
    secret_key:str,
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)
    response = generate_api_key(db, transform_user, secret_key)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "You created api key successfully.",
            "payload": response,
            "success": True,
        }
    )
