# app/schemas/project_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
 
from app.config.constant import PROJECT_STATUS_ACTIVE, TASK_STATUS, DEPENDENCY_TYPE
from app.schemas.label_schema import LabelMappingBase, ProjectLabelIn, SimpleLabelOut
 
 
# ────────────────────── TASK SCHEMAS ──────────────────────
class TaskBase(BaseModel):
    task_name: str
    dependency_type: Optional[int] = None
    is_milestone: bool | None = None
    depends_on: int | None = None      
    days_offset: int | None = None
    parent_id: Optional[int] = None
    status_id: Optional[int] = None
    priority_id: Optional[int | str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_by: Optional[str] = None
    depends_on: Optional[int] = None
 
 
class TaskCreate(TaskBase):
    # created_by_user_id: int
    user_ids: List[int] = []
    pass
 
class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    priority_id: Optional[int] = None
    status_id: Optional[int] = None
    is_milestone: Optional[bool] = None
    # modified_by_user_id: Optional[int] = None
    modified_at: Optional[datetime] = None
    parent_id: Optional[int] = None
    depends_on: Optional[int] = None
    dependency_type: Optional[int] = None
    days_offset: Optional[int] = None
    sort_order: Optional[int] = None          
    subtask_sort_order: Optional[int] = None
    user_ids: List[int] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
 
class TaskUserOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    task_id: int
    created_by: Optional[str] = None
    created_at: datetime
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    is_active: bool
    is_milestone: bool | None = None
    depends_on: int | None = None      
    days_offset: int | None = None
    dependency_type: Optional[int] = None
    profile_picture: Optional[str] = None
    profile_picture_url: Optional[str] = None
 
    model_config = {"from_attributes": True}
 
 
class TaskOut(BaseModel):
    task_name: str
    id: int
    project_id: int
    created_at: datetime
    modified_at: Optional[datetime] = None
    is_active: bool
 
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    is_milestone: Optional[bool] = None
    dependency_type: Optional[int] = None
    dependent_task_id: Optional[int] = None
    days_offset: Optional[int] = None
    depends_on: Optional[int] = None
    sort_order: Optional[int] = None          
    subtask_sort_order: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    subtasks: List["TaskOut"] = Field(default_factory=list)
    users: List[TaskUserOut] = Field(default_factory=list)
    labels: List[SimpleLabelOut] = Field(default_factory=list)
    created_by_profile_picture: Optional[str] = None
    created_by_profile_picture_url: Optional[str] = None
    model_config = {"from_attributes": True}
 
 
TaskOut.model_rebuild()
 
# ────────────────────── PROJECT SCHEMAS ──────────────────────
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status_id: int
 
class ProjectCreate(ProjectBase):
    created_by: Optional[str] = None
    # user_id: int
    labels: List[ProjectLabelIn] = Field(default_factory=list)
 
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status_id: Optional[int] = None
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    sort_order: Optional[int] = None
 
class ProjectOut(ProjectBase):
    id: int
    created_by: Optional[str]
    modified_by: Optional[str]
    created_at: datetime
    modified_at: Optional[datetime] = None
    is_active: bool
    status_id: Optional[int] = PROJECT_STATUS_ACTIVE  
    # user_id: Optional[int] = None
    tasks: List[TaskOut] = []
    labels: List[SimpleLabelOut] = Field(default_factory=list)
    sort_order: Optional[int] = None
    model_config = {"from_attributes": True}
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
 
 
class ProjectCopyOptions(BaseModel):
    source_project_id: Optional[int] = None
    source_task_id: Optional[int] = None    
    copy_project: bool = True
    copy_tasks: bool = True
    copy_subtasks: bool = True
    # user_id: int
 
 
class ProjectReorderItem(BaseModel):
    project_id: Optional[int] = None      
    task_id: Optional[int] = None        
    parent_task_id: Optional[int] = None
    position: int                        
 
class ProjectReorderRequest(BaseModel):
    # user_id: Optional[int] = None
    items: List[ProjectReorderItem]
 
 