# app/helpers/auth.py
 
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt   # pip install python-jose
from app.database import get_db
from app.models.user import User
from app.schemas.authschema import CurrentUser
 
security = HTTPBearer()
 
def _decode_jwt_payload(token: str) -> dict:
    try:
        claims = jwt.get_unverified_claims(token)
        return claims
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )
 
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    token = credentials.credentials
    claims = _decode_jwt_payload(token)
 
    username = (
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
    )
    email = claims.get("email") or username
    oid = claims.get("oid")
 
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/email not found in token",
        )
 
    user = (
        db.query(User)
        .filter(User.username == username, User.is_active == True)
        .first()
    )
 
    # optional auto-create local user
    if not user:
        user = User(
            username=username,
            status_id=None,
            created_by=username,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
 
    return CurrentUser(
        user_id=user.user_id,
        username=user.username,
        email=email,
        oid=oid,
    )
 
 