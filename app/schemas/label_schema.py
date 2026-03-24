# app/schemas/label_schema.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

# LABEL 
class LabelBase(BaseModel):
    label_text: str = Field(..., max_length=255)
    category_id: Optional[int] = None

class LabelCreate(LabelBase):
    # created_by_user_id: Optional[int]  
    pass

class LabelUpdate(BaseModel):
    label_text: Optional[str] = Field(None, max_length=255)
    category_id: Optional[int]
    # modified_by_user_id: Optional[int]

class LabelOut(BaseModel):
    labels_id: int
    label_text: str
    category_id: int
    created_by: Optional[str]
    created_at: Optional[datetime]
    modified_by: Optional[str]
    modified_at: Optional[datetime]
    is_active: bool
    sort_order: Optional[int]
    model_config = ConfigDict(from_attributes=True)

# LABEL <-> PROJECT/TASK MAPPING 
class LabelMappingBase(BaseModel):
    label_id: int
    project_id: int
    task_id: Optional[int] = None
    project_label_category_id: Optional[int] = None

class LabelMappingCreate(LabelMappingBase):
    # created_by_user_id: Optional[int]

    # class Config:
    #     from_attributes = True
    model_config = ConfigDict(from_attributes=True)

class LabelMappingUpdate(BaseModel):
    label_id: Optional[int] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    project_label_category_id: Optional[int] = None
    # modified_by_user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class LabelMappingOut(LabelMappingBase):
    labels_project_task_mapping_id: int
    # label_id: int
    # project_id: int
    # task_id: Optional[int]
    project_label_category_id: Optional[int]

    created_by: Optional[str]
    created_at: Optional[datetime]
    modified_by: Optional[str]
    modified_at: Optional[datetime]
    is_active: bool
    sort_order: Optional[int]
    model_config = ConfigDict(from_attributes=True)


class SimpleLabelOut(BaseModel):
    label_id: int
    label_text: str
    project_label_category_id: Optional[int] = None
    labels_project_task_mapping_id: int
    sort_order: Optional[int]
    model_config = ConfigDict(from_attributes=True)

class ProjectLabelIn(BaseModel):
    label_id: int
    project_label_category_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# class ProjectLabelSwapRequest(BaseModel):
#     source_label_id: Optional[int] = None
#     source_sort_order: Optional[int] = None
#     target_label_id: Optional[int] = None
#     target_sort_order: Optional[int] = None

# class TaskLabelSwapRequest(BaseModel):
#     source_mapping_id: Optional[int] = None
#     source_sort_order: Optional[int] = None
#     target_mapping_id: Optional[int] = None
#     target_sort_order: Optional[int] = None


class ProjectLabelReorderItem(BaseModel):
    label_id: int
    position: int

class ProjectLabelReorderRequest(BaseModel):
    items: List[ProjectLabelReorderItem]

class TaskLabelReorderItem(BaseModel):
    mapping_id: int   
    position: int

class TaskLabelReorderRequest(BaseModel):
    items: List[TaskLabelReorderItem]