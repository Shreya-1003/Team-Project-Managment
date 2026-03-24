# app/routes/system_constant_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.system_constant import SystemConstant


router = APIRouter(prefix="/api/system-constant",tags=["System Constant"])

@router.get("", response_model=list[dict])
def get_system_constants(db: Session = Depends(get_db)):
    constants = db.query(SystemConstant).filter(SystemConstant.is_active == True).all()
    return [
        {
            "id": c.id,
            "type": c.type,
            "name": c.name,
            "status": c.status
        }
        for c in constants
    ]