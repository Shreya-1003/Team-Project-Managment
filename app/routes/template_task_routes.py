from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.template import Template
from app.models.template_task_mapping import TemplateTaskMapping
from app.schemas.template_schema import TemplateCreate, TemplateOut, TemplateReorderRequest, TemplateUpdate, TemplateTaskCreate, TemplateTaskOut, TemplateTaskUpdate,TemplateCopyOptions
from app.models.user import User  
from sqlalchemy import case,func
from app.config.constant import TASK_PRIORITY_HIGH, TASK_STATUS, DEPENDENCY_TYPE
from app.models.system_constant import SystemConstant
from datetime import datetime
from app.services.template_task_service import TemplateTaskService
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser


router = APIRouter(tags=["Templates & Tasks"])

@router.post("/{template_id}/tasks", response_model=TemplateTaskOut, status_code=201)
async def create_task(template_id: int, payload: TemplateTaskCreate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return await TemplateTaskService.create_task(template_id, payload, db,current_user=current_user)

@router.get("/{template_id}/tasks", response_model=List[TemplateTaskOut])
def list_tasks(template_id: int, db: Session = Depends(get_db)):
    return TemplateTaskService.list_tasks(template_id, db)

@router.get("/{template_id}/tasks/{task_id}", response_model=TemplateTaskOut)
async def get_task(template_id: int, task_id: int, db: Session = Depends(get_db)):
    return await TemplateTaskService.get_task(template_id, task_id, db)

@router.put("/{template_id}/tasks/{task_id}", response_model=TemplateTaskOut)
async def update_task(template_id: int, task_id: int, payload: TemplateTaskUpdate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return await TemplateTaskService.update_task(template_id, task_id, payload, db, current_user=current_user)   

@router.delete("/{template_id}/tasks/{task_id}", status_code=204)
async def delete_task(template_id: int, task_id: int, db: Session = Depends(get_db)):
    return await TemplateTaskService.delete_task(template_id, task_id, db)