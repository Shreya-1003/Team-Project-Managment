# app/schemas/permission_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from typing import Optional, List

class PermissionBase(BaseModel):
    permission_type: str = Field(..., min_length=1, max_length=100)
    permission_bracket: Optional[str] = None

class PermissionCreate(PermissionBase):
    created_by: Optional[str] = None
    created_by_user_id: int 
    # user_ids: Optional[List[int]] = None  

class PermissionUpdate(BaseModel):
    permission_type: Optional[str] = None
    permission_bracket: Optional[str] = None
    is_active: Optional[bool] = None
    modified_by: Optional[str] = None
    modified_by_user_id: int 
  

class PermissionOut(BaseModel):
    id: int
    permission_type: str = Field(..., min_length=1, max_length=100)
    permission_bracket: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Config:
        from_attributes = True