from app.auth.models import User

def insert_api_key(db, user, api_key):
    user = db.query(User).filter(User.id == user.id).first()
    
    if not user:
        return None  # Or raise an appropriate exception

    # Check if the field exists in the User model
    if not hasattr(user, "api_key"):
        raise ValueError("Field 'api_key' does not exist in User model.")
    
    setattr(user, "api_key", api_key)
    
    db.commit()
    db.refresh(user)
    return user