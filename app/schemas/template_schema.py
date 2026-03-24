from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class LookupResponse(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True


class TemplateTaskBase(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    priority_id: Optional[int] = None
    isMilestone: Optional[bool] = None
    dependent_taskid: Optional[int] = None
    dependency_type: Optional[int] = None
    days_offset: Optional[int] = 0
    parent_id: Optional[int] = None
    status_id: Optional[int] = None


class TemplateTaskCreate(TemplateTaskBase):
    # user_id: int
    depends_on: Optional[int] = None  
    subtasks: Optional[List["TemplateTaskCreate"]] = []


class TemplateTaskUpdate(TemplateTaskBase):
    depends_on: Optional[int] = None
    # modified_by_user_id: Optional[int] = None


class TemplateTaskOut(TemplateTaskBase):
    template_task_mapping_id: int
    priority: Optional[LookupResponse] = None
    status: Optional[LookupResponse] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    is_active: bool
    subtasks: List["TemplateTaskOut"] = Field(default_factory=list)
    sort_order: Optional[int] = None             
    subtask_sort_order: Optional[int] = None

    class Config:
        from_attributes = True


TemplateTaskOut.update_forward_refs()


class TemplateBase(BaseModel):
    template_name: Optional[str] = Field(None, max_length=255)
    template_description: Optional[str] = None


class TemplateCreate(TemplateBase):
    # user_id: int
    created_by: Optional[str] = None
    tasks: Optional[List[TemplateTaskCreate]] = []


class TemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    template_description: Optional[str] = None
    # modified_by_user_id: Optional[int] = None
    is_active: Optional[bool] = None


class TemplateOut(TemplateBase):
    template_id: int
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    is_active: bool
    tasks: List[TemplateTaskOut] = []
    sort_order: Optional[int] = None

    class Config:
        from_attributes = True

class TemplateCopyOptions(BaseModel):
    source_template_id: Optional[int] = None   
    source_task_id: Optional[int] = None      
    copy_tasks: bool = True                    
    copy_subtasks: bool = True                 
    # user_id: int


class ReorderItem(BaseModel):
    id: int
    sort_order: int



class TemplateReorderItem(BaseModel):
    template_id: int
    position: int

class TemplateTaskReorderItem(BaseModel):
    template_id: int
    task_id: int
    parent_task_id: Optional[int] = None
    position: int

class TemplateReorderRequest(BaseModel):
    items: List[TemplateTaskReorderItem | TemplateReorderItem]