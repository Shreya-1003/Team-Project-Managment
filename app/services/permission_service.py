# app/services/permission_service.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import insert, delete, select
from app.database import get_db
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission_mapping import UserPermissionMapping
from app.schemas.permission_schema import PermissionCreate, PermissionOut, PermissionUpdate
from typing import List

class PermissionService:
    @staticmethod
    def create_permission(
        payload: PermissionCreate,db: Session = Depends(get_db)):
        creator = (
            db.query(User)
            .filter(User.user_id == payload.created_by_user_id, User.is_active == True)
            .first()
        )
        if not creator:
            raise HTTPException(404, "Creator user not found")

        data = payload.model_dump(exclude={"created_by_user_id"})
        data["created_by"] = creator.username

        perm = Permission(**data)
        db.add(perm)
        db.commit()
        db.refresh(perm)
        return perm


    @staticmethod
    def list_permissions(db: Session = Depends(get_db)):
        return (
            db.query(Permission)
            .filter(Permission.is_active == True)
            .all()
        )

    # @staticmethod
    # def get_permission(permission_id: int, db: Session = Depends(get_db)):
    #     perm = db.get(Permission, permission_id)
    #     if not perm or not perm.is_active:
    #         raise HTTPException(404, "Permission not found or inactive")
    #     out = PermissionOut.from_orm(perm)
    #     out.user_ids = _get_user_ids(db, permission_id)
    #     return out

    # @staticmethod
    # def update(db: Session, permission_id: int, payload: PermissionUpdate) -> Optional[PermissionOut]:  
    #     obj = db.query(PermissionModel).filter(PermissionModel.id == permission_id).first()
    #     if not obj: return None
    #     for key, value in payload.dict(exclude_unset=True).items():
    #         setattr(obj, key, value)
    #     obj.modified_at = datetime.utcnow()
    #     db.commit()
    #     db.refresh(obj)
    #     return PermissionOut.from_orm(obj)

    # @staticmethod
    # def delete(db: Session, permission_id: int) -> bool:  
    #     obj = db.query(PermissionModel).filter(PermissionModel.id == permission_id).first()
    #     if not obj: return False
    #     obj.is_active = False
    #     db.commit()
    #     return True