import jwt

from .crud import insert_api_key

def generate_api_key(db, current_user, SECRET_KEY):
    print( current_user)
    data = {
        "email": current_user.email,
        "username": current_user.username
    }
    api_key = create_api_key(data, SECRET_KEY)
    
    user = insert_api_key(db,current_user, api_key)
    return api_key

def create_api_key(data: dict, SECRET_KEY):
    to_encode = data.copy()
    ALGORITHM = "HS256"
    # Encode the token
    api_key = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return api_key