# app/routes/permission_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import insert, delete, select
from app.database import get_db
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission_mapping import UserPermissionMapping
from app.schemas.permission_schema import PermissionCreate, PermissionOut, PermissionUpdate
from typing import List
from app.services.permission_service import PermissionService
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser


router = APIRouter(tags=["Permissions"])


@router.post("", response_model=PermissionOut, status_code=status.HTTP_201_CREATED)
def create_permission(payload: PermissionCreate,db: Session = Depends(get_db)):
   return PermissionService.create_permission(payload=payload, db=db)


@router.get("", response_model=list[PermissionOut])
def list_permissions(db: Session = Depends(get_db)):
    return PermissionService.list_permissions(db=db)


# @router.get("/{permission_id}", response_model=PermissionOut)
# def get_permission(permission_id: int, db: Session = Depends(get_db)):
#     return PermissionService.get_permissions(db=db)


# @router.put("/{permission_id}", response_model=PermissionOut)
# def update_permission(
#     permission_id: int,
#     payload: PermissionUpdate,
#     db: Session = Depends(get_db),
# ):
#     return perm


# @router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_permission(permission_id: int, db: Session = Depends(get_db)):
#     return None
