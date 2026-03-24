from typing import List
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query
from app.services.project_service import ProjectService
from app.schemas.project_schema import  ProjectReorderRequest
from app.schemas.project_schema import ProjectCreate, ProjectOut, ProjectUpdate, ProjectCopyOptions
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser
 
 
router = APIRouter(tags=["Projects & Tasks"])
 
@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(  # ✅ Add async
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ProjectService.create_project(payload, db, current_user)
 
 
@router.post("/copy", status_code=201)
async def copy_project(
    payload: ProjectCopyOptions,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ProjectService.copy_project(payload=payload, db=db, current_user=current_user)
   
@router.get("", response_model=List[ProjectOut])
async def list_projects(
    db: Session = Depends(get_db),
    created_by: str | None = Query(default=None),
    due_filters: List[str] = Query(default_factory=list),
    assigned_user_id: int | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    # due_filters: List[str] = Query(default_factory=list)(
    #     default=None,
    #     description="late | today | tomorrow | this_week | next_week | future | no_date",
    # ),
):
    if due_filters and ',' in ','.join(due_filters):
        due_filters = [f.strip() for filter_str in due_filters 
                      for f in filter_str.split(',')]
    return await ProjectService.list_projects(
        db=db,
        user_id=None,
        assigned_user_id=assigned_user_id,
        current_user=current_user,
        created_by=created_by,  
        due_filters=due_filters,    
    )
 
@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ProjectService.get_project(project_id=project_id, db=db, current_user=current_user)
   
@router.put("/reorder", status_code=204)
def reorder_projects(
    payload: ProjectReorderRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return ProjectService.reorder_projects(
        payload=payload,
        db=db,
        current_user=current_user,
    )
@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ProjectService.update_project(
        project_id=project_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )
 
@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    return await ProjectService.delete_project(project_id=project_id, db=db)