from fastapi import APIRouter, Depends, HTTPException, Header
from requests import Session
from app.database import get_db
from app.helpers.auth import get_current_user
from app.helpers.utils import get_microsoft_user,  get_microsoft_user_photo_proxy, upload_user_photo_to_blob
from app.models.user import User
from app.services.ms_service import MsService
from app.services.user_service import UserService
 
router = APIRouter(tags=["Microsoft Graph"])
 
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user_data = get_microsoft_user(user_id)
    return user_data

@router.get("/users/{user_id}/photo/")
def get_user_photo(user_id: str):
    return get_microsoft_user_photo_proxy(user_id)

@router.post("/users/{user_id}/photo/upload")  
async def upload_user_photo(
    user_id: str,  
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == user_id).first()  
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = upload_user_photo_to_blob(user_id, db, user)
    return result