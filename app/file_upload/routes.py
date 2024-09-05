from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi import Depends
from app.auth.dependencies import get_current_active_user
from app.auth.schemas import User, ChromaSchemaDB
from typing import Annotated
from app.utils import get_db
from sqlalchemy.orm import Session
from . import dependencies
from app.auth.dependencies import get_current_active_user, transform_user_dto
from app.auth.crud import get_user_by_email
from app.auth.models import ChromaDB

router = APIRouter(
    prefix="/files",
    tags={"file"}, 
)


@router.post("/file_upload")
async def file_upload(
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
    
@router.post("/file_upload_to_chroma")
async def file_upload_to_chroma(
    session_id,
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...), 
    db: Session = Depends(get_db) 
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)
    chroma_data = dependencies.upload_file_to_chroma(db,file, transform_user, session_id)
    
    chroma_data_serialized = ChromaSchemaDB.model_validate(chroma_data).model_dump()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content = {
            "message": "File uploaded successfully",
            "success": True,
            "payload": chroma_data_serialized,
        },
    )

@router.get("/get_all_chroma_by_current_user")
async def get_all_chroma_by_user_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)
    chroma_list = dependencies.get_all_chromas(db, transform_user.id)
    chroma_data_serialized = [ChromaSchemaDB.model_validate(chroma).model_dump() for chroma in chroma_list]
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content = {
            "message": "File uploaded successfully",
            "success": True,
            "payload": chroma_data_serialized,
        },
    )
    
@router.delete("/delete_chroma_database")
async def delete_chroma_by_chroma_name(
    chroma_name: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)
    dependencies.delete_chroma_by_chroma_name(db,chroma_name,transform_user.id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content = {
            "message": "Chroma database was deleted successfully",
            "success": True,
        },
    )