from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi import Depends
from app.auth.dependencies import get_current_active_user
from app.auth.schemas import User
from typing import Annotated
from app.utils import get_db
from sqlalchemy.orm import Session
from . import dependencies

router = APIRouter(
    prefix="/files",
    tags={"file"}, 
)


@router.post("/file_upload")
def file_upload(
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...), 
    db: Session = Depends(get_db) 
):
    response = dependencies.file_upload_to_db(db, file, current_user)  
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content = {
            "message": "File uploaded successfully",
            "success": True,
            "filename": response,
        },
    )
    

        