from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Query, status, Depends
from app.schemas.user_schema import UserPermissionUpdateResult
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserTaskCreate,
    UserTaskUpdate,
    UserTaskResponse,
    UserPermissionCreate,
    UserPermissionUpdate,
)
from app.services.user_service import UserService
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser
from app.helpers.utils import validate_user
from app.models.user import User
 
router = APIRouter(tags=["Users"])
 
# ---------- USERS ----------


 
@router.put("/user-permissions", response_model=list[UserPermissionUpdateResult])
def update_user_permissions(
    payload: UserPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    return UserService.update_user_permissions(payload, db, current_user)

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return UserService.create_user(payload=payload, db=db, current_user=current_user)
 
@router.get("", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return UserService.get_all_users(db)
 
 
@router.get("/by-id", response_model=UserResponse)
def get_user(db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return UserService.get_user(db=db,current_user=current_user)
 
@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return UserService.update_user(
        user_id=user_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )
 
 
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return UserService.delete_user(user_id, db)
 
 
# ---------- ASSIGN USER TO TASK  ----------
 
@router.post(
    "/{user_id}/tasks/{task_id}",
    response_model=UserTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_user_to_task(
    user_id: int,
    task_id: int,
    payload: UserTaskCreate,
    db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user),
):
    return UserService.assign_user_to_task(user_id, task_id, payload, db,current_user=current_user, )
 
@router.get(
    "/{user_id}/tasks",
    response_model=list[UserTaskResponse],
)
def list_user_task_mappings(user_id: int, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user),):
    return UserService.list_user_task_mappings(user_id, db)
 
@router.put(
    "/user-task-mappings/{mapping_id}",
    response_model=UserTaskResponse,
)
def update_user_task_mapping(
    mapping_id: int,
    payload: UserTaskUpdate,
    db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)
):
    return UserService.update_user_task_mapping(mapping_id, payload, db, current_user=current_user,)
 
 
@router.delete(
    "/user-task-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_task_mapping(mapping_id: int, db: Session = Depends(get_db)):
    return UserService.delete_user_task_mapping(mapping_id, db)
 
 
# ---------- USER <-> PERMISSION MAPPING ----------
 
@router.post(
    "/permissions",
    status_code=status.HTTP_201_CREATED,
)
def create_user_permissions(
    payload: UserPermissionCreate,
    db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)
):
    return UserService.create_user_permissions(payload, db,current_user=current_user,)
 

 
 
#--------------- check user exists -------------
 
@router.get("/check")
def user_check(username: str = Query(...), db: Session = Depends(get_db)):  
    return UserService.user_check(username, db)