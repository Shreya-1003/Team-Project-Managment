# app/routes/template_routes.py
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
from app.services.template_service import TemplateService
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser

router = APIRouter(tags=["Templates & Tasks"])

@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(payload: TemplateCreate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return await TemplateService.create_template(payload, db,current_user=current_user,)


@router.post("/copy", status_code=201, response_model=TemplateOut | TemplateTaskOut)
async def copy_template(payload: TemplateCopyOptions, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return await TemplateService.copy_template(payload, db,current_user=current_user)


@router.get("", response_model=List[TemplateOut])
async def list_templates(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return await TemplateService.list_templates(db,current_user=current_user)


@router.put("/reorder", status_code=204)
def reorder_templates(
    payload: TemplateReorderRequest,
    db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)
):
    return TemplateService.reorder_templates(payload, db,current_user=current_user)

@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: int, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user)):
    return await TemplateService.get_template(template_id, db,current_user=current_user)

@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(template_id: int, payload: TemplateUpdate, db: Session = Depends(get_db),current_user: CurrentUser = Depends(get_current_user),):
    return await TemplateService.update_template(template_id, payload, db,current_user=current_user,)

@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    return await TemplateService.delete_template(template_id, db)  
    
