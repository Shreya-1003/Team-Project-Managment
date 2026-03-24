# app/routes/label_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.label import Label
from app.models.labels_project_task_mapping import LabelsProjectTaskMapping
from app.models.user import User
from app.models.system_constant import SystemConstant
from app.models.project import Project
from app.models.project_task_mapping import ProjectTaskMapping
from app.schemas.label_schema import (
    LabelCreate, LabelOut, LabelUpdate,
    LabelMappingCreate, LabelMappingOut,  ProjectLabelReorderRequest, TaskLabelReorderRequest
)
from app.config.constant import (
    LABEL_CATEGORY,
    LABEL_CATEGORY_DEFAULT,
    PROJECT_LABEL_CATEGORY,
    PROJECT_LABEL_CATEGORY_DEFAULT
)

from datetime import datetime
from app.services.label_service import LabelService
from app.services.project_task_mapping_service import ProjectTaskMappingService
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser


router = APIRouter(tags=["Labels"])

@router.post("/mappings", response_model=LabelMappingOut, status_code=201)
def create_label_mapping(payload: LabelMappingCreate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return ProjectTaskMappingService.create_label_mapping(payload, db,current_user=current_user,)

@router.get("/mappings", response_model=List[LabelMappingOut])
def list_mappings(db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return ProjectTaskMappingService.list_mappings(db,current_user=current_user)


@router.get("/mappings/{mapping_id}", response_model=LabelMappingOut)
def get_mapping(mapping_id: int, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return ProjectTaskMappingService.get_mapping(mapping_id, db,current_user=current_user)

@router.put("/mappings/{mapping_id}", response_model=LabelMappingOut)
def update_label_mapping(mapping_id: int, payload: LabelMappingCreate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return ProjectTaskMappingService.update_label_mapping(mapping_id, payload, db, current_user=current_user)

@router.put("/project-labels/reorder", status_code=204)
def reorder_project_labels(
    payload: ProjectLabelReorderRequest,
    db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)
):
    return ProjectTaskMappingService.reorder_project_labels(payload, db,current_user=current_user)

@router.put("/task-labels/reorder", status_code=204)
def reorder_task_labels(
    payload: TaskLabelReorderRequest,
    db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)
):
    return ProjectTaskMappingService.reorder_task_labels(payload, db,current_user=current_user)
    
@router.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    return ProjectTaskMappingService.delete_mapping(mapping_id, db)

