# app/routes/project_routes.py
from typing import List
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.services.project_task_service import ProjectTaskService
from app.schemas.project_schema import TaskCreate, TaskOut, TaskUpdate
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser

router = APIRouter(tags=["Projects & Tasks"])

@router.post("/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_task(
    project_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ProjectTaskService.create_task(
        project_id=project_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )

@router.get("/{project_id}/tasks", response_model=List[TaskOut])
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    return ProjectTaskService.list_tasks(project_id=project_id, db=db)  

@router.put("/{project_id}/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    project_id: int,
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await ProjectTaskService.update_task(
        project_id=project_id,
        task_id=task_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.delete("/{project_id}/tasks/{task_id}", status_code=204)
async def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db)
):
    await ProjectTaskService.delete_task(
        task_id=task_id,
        db=db,
        project_id=project_id 
    )
    return
