import jwt

from .crud import insert_api_key
from langchain_groq import ChatGroq



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


from .schemas import Provider, Model
def custom_chat(provider: Provider, model: Model, API_KEY: str):
    
    if provider.value is "groq":
        
        return ChatGroq(
            model=model.value,
            api_key=API_KEY
        )
    