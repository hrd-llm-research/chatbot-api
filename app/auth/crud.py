from . import models, schemas, dependencies
from sqlalchemy.orm import Session

def get_user_email(db: Session, email: str):
    user_db = db.query(models.User).filter(models.User.email == email).first()
    return user_db
    

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = dependencies.pwd_context.hash(user.password)
    db_user = models.User(username=user.username, password=hashed_password, email=user.email)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

