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
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser



router = APIRouter(tags=["Labels"])

# -------- LABEL CRUD --------

@router.post("", response_model=LabelOut, status_code=201)
def create_label(payload: LabelCreate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return LabelService.create_label(payload, db,current_user=current_user)

@router.get("", response_model=List[LabelOut])
def list_labels(db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return LabelService.list_labels(db,current_user=current_user)

@router.get("/{label_id}", response_model=LabelOut)
def get_label(label_id: int, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return LabelService.get_label(label_id, db, current_user=current_user)

@router.put("/{label_id}", response_model=LabelOut)
def update_label(label_id: int, payload: LabelUpdate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return LabelService.update_label(label_id, payload, db,current_user=current_user)

@router.delete("/{label_id}", status_code=204)
def delete_label(label_id: int, db: Session = Depends(get_db)):
    return LabelService.delete_label(label_id, db)

