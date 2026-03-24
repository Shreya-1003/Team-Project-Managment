from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
 
# ---- USERS ----
 
class UserBase(BaseModel):
    username: str
    status_id: Optional[int] = None
 
class UserCreate(UserBase):
    pass
 
class UserUpdate(BaseModel):
    username: Optional[str] = None
    status_id: Optional[int] = None
 
class UserResponse(BaseModel):
    user_id: int
    username: str
    status_id: Optional[int]
    created_by: Optional[str]
    created_at: datetime
    modified_by: Optional[str]
    modified_at: Optional[datetime]
    permission_mapping_ids: list[int] = []
    permission_ids: list[int] = []
    is_active: bool
    permission_types: List[str] = []
    permission_brackets: List[str] = []
    profile_picture: Optional[str] = None
    profile_picture_url: Optional[str] = None
    model_config = {"from_attributes": True}
 
# ---- USER <-> TASK MAPPING ----
 
class UserTaskBase(BaseModel):
    user_id: int
    task_id: int
 
class UserTaskCreate(UserTaskBase):
    # created_by_user_id: Optional[int] = None
    pass
 
class UserTaskUpdate(BaseModel):
    user_id: Optional[int] = None
    task_id: Optional[int] = None
    # modified_by_user_id: Optional[int] = None
 
class UserTaskResponse(UserTaskBase):
    id: int
    created_by: Optional[str]
    created_at: datetime
    modified_by: Optional[str]
    modified_at: Optional[datetime]
    is_active: bool
    task_id: Optional[int] = None
    profile_picture: Optional[str] = None      
    profile_picture_url: Optional[str] = None
    model_config = {"from_attributes": True}
 
 
# ---- USER <-> PERMISSION MAPPING ----
 
class UserPermissionBase(BaseModel):
    user_id: int
    permission_id: List[int]
 
class UserPermissionCreate(UserPermissionBase):
    # created_by_user_id: Optional[int] = None
    pass
 
class SinglePermissionChange(BaseModel):
    mapping_id: int
    is_active: Optional[bool] = None
    permission_id: Optional[int] = None
 
class UserPermissionUpdate(BaseModel):
    user_id: int  
    changes: List[SinglePermissionChange]  
    # modified_by_user_id: Optional[int] = None
 
 
class UserPermissionUpdateResult(BaseModel):
    user_id: Optional[int] = None
    permission_ids: list[int]
    is_active: Optional[bool] = None
 
class UserPermissionResponse(BaseModel):
    id: int
    user_id: int
    permission_id: List[int]
    created_by: str | None = None
    modified_by: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    is_active: Optional[bool] = None
 
    class Config:
        from_attributes = True
 