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
from app.schemas.authschema import CurrentUser
from app.websockets.manager import manager


class TemplateTaskService:
    @staticmethod
    async def create_task(template_id: int, payload: TemplateTaskCreate, db: Session ,current_user: CurrentUser):
        # user = db.query(User).filter(User.user_id == payload.user_id).first()
        # if not user:
        #     raise HTTPException(status_code=404, detail="User not found")

        data = payload.dict()
        data.pop("user_id", None)
        data["template_id"] = template_id
        data["priority_id"] = data.get("priority_id", TASK_PRIORITY_HIGH)
        data["status_id"] = data.get("status_id", TASK_STATUS)
        data["created_by"] = current_user.username

        dep_type_value = data.get("dependency_type")  

        if dep_type_value is None:
            data["dependency_type"] = None
        else:
            if isinstance(dep_type_value, int):
                data["dependency_type"] = dep_type_value
            else:
                dep_row = (
                    db.query(SystemConstant)
                    .filter(
                        SystemConstant.type == DEPENDENCY_TYPE,    
                        SystemConstant.name == dep_type_value,
                        SystemConstant.is_active == True,
                    )
                    .first()
                )
                if not dep_row:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid dependency type"
                    )
                data["dependency_type"] = dep_row.id

        depends_on = data.pop("depends_on", None)
        if depends_on:
            dep_task = (
                db.query(TemplateTaskMapping)
                .filter(
                    TemplateTaskMapping.template_task_mapping_id == depends_on,
                    TemplateTaskMapping.template_id == template_id,
                    TemplateTaskMapping.is_active == True,
                )
                .first()
            )
            if not dep_task:
                raise HTTPException(status_code=404, detail="Dependent task not found in this template")
            data["dependent_taskid"] = depends_on
        else:
            data["dependent_taskid"] = None


        parent_id = data.get("parent_id")

        if parent_id:
            parent = (
                db.query(TemplateTaskMapping)
                .filter(
                    TemplateTaskMapping.template_task_mapping_id == parent_id,
                    TemplateTaskMapping.template_id == template_id,
                    TemplateTaskMapping.is_active == True,
                )
                .first()
            )
            if not parent:
                raise HTTPException(status_code=404, detail="Parent task not found in this template")
            if data.get("days_offset") is None:
                data["days_offset"] = 0


        if data.get("parent_id"):
            max_sort = (
                db.query(func.max(TemplateTaskMapping.sort_order))
                .filter(
                    TemplateTaskMapping.template_id == template_id,
                    TemplateTaskMapping.parent_id == data["parent_id"],
                    TemplateTaskMapping.is_active == True,
                )
                .scalar()
            )
        else:
            max_sort = (
                db.query(func.max(TemplateTaskMapping.sort_order))
                .filter(
                    TemplateTaskMapping.template_id == template_id,
                    TemplateTaskMapping.parent_id == None,
                    TemplateTaskMapping.is_active == True,
                )
                .scalar()
            )

        data["sort_order"] = (max_sort or 0) + 1

        task = TemplateTaskMapping(**data)
        db.add(task)
        db.commit()
        db.refresh(task)
        payload = {
            "type": "template_task_create",
            "template_id": template_id,
            "task_id": task.template_task_mapping_id,
            "task_name": task.task_name,
            "created_by": current_user.username
        }

        # ✅ Add parent_id ONLY if task has parent (exactly like your project copy)
        if task.parent_id is not None:
            payload["parent_id"] = task.parent_id

        await manager.broadcast(payload)
        print(f"🔥 Broadcasted template_task_create: task_id={task.template_task_mapping_id}, parent_id={task.parent_id}")

        return TemplateTaskOut.from_orm(task)

    
    @staticmethod
    def list_tasks(template_id: int, db: Session = Depends(get_db)):
        tasks = (
            db.query(TemplateTaskMapping)
            .options(joinedload(TemplateTaskMapping.subtasks))
            .filter(TemplateTaskMapping.template_id == template_id, TemplateTaskMapping.is_active == True)
            .all()
        )
        return [TemplateTaskOut.from_orm(t) for t in tasks]
    
    @staticmethod
    async def get_task(template_id: int, task_id: int, db: Session = Depends(get_db)):
        task = (
            db.query(TemplateTaskMapping)
            .options(
                joinedload(TemplateTaskMapping.priority),
                joinedload(TemplateTaskMapping.status),
                joinedload(TemplateTaskMapping.subtasks),
            )
            .filter(
                TemplateTaskMapping.template_task_mapping_id == task_id,
                TemplateTaskMapping.template_id == template_id,
                TemplateTaskMapping.is_active == True,
            )
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        await manager.broadcast({
            "type": "template_task_viewed",
            "template_id": template_id,
            "task_id": task_id,
            "task_name": task.task_name
        })
        print(f"🔥 Broadcasted template_task_viewed event: task_id={task_id}")
        return TemplateTaskOut.from_orm(task)
    
    @staticmethod
    async def update_task(
        template_id: int,
        task_id: int,
        payload: TemplateTaskUpdate,
        db: Session , current_user: CurrentUser,
    ):
        task = (
            db.query(TemplateTaskMapping)
            .filter(
                TemplateTaskMapping.template_task_mapping_id == task_id,
                TemplateTaskMapping.template_id == template_id,
            )
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        update_data = payload.dict(exclude_unset=True)

        # if hasattr(payload, "modified_by_user_id") and payload.modified_by_user_id:
        #     user = (
        #         db.query(User)
        #         .filter(User.user_id == payload.modified_by_user_id)
        #         .first()
        #     )
        #     if not user:
        #         raise HTTPException(status_code=404, detail="User not found")
        #     update_data["modified_by"] = user.username

        update_data.pop("modified_by_user_id", None)
        update_data.pop("modified_by", None)

        task.modified_by = current_user.username
        
        if "priority_id" not in update_data:
            update_data["priority_id"] = task.priority_id or TASK_PRIORITY_HIGH

        if "status_id" not in update_data:
            update_data["status_id"] = task.status_id or TASK_STATUS

        if "dependency_type" in update_data:
            dep_type_value = update_data["dependency_type"]
            if dep_type_value is None:
                update_data["dependency_type"] = None
            else:
                if isinstance(dep_type_value, int):
                    update_data["dependency_type"] = dep_type_value
                else:
                    dep_row = (
                        db.query(SystemConstant)
                        .filter(
                            SystemConstant.type == DEPENDENCY_TYPE,
                            SystemConstant.name == dep_type_value,
                            SystemConstant.is_active == True,
                        )
                        .first()
                    )
                    if not dep_row:
                        raise HTTPException(
                            status_code=400, detail="Invalid dependency type"
                        )
                    update_data["dependency_type"] = dep_row.id

        for key, value in update_data.items():
            setattr(task, key, value)

        if "depends_on" in update_data:
            new_dep = update_data["depends_on"]
            if new_dep:
                dep_task = (
                    db.query(TemplateTaskMapping)
                    .filter(
                        TemplateTaskMapping.template_task_mapping_id == new_dep,
                        TemplateTaskMapping.template_id == template_id,
                        TemplateTaskMapping.is_active == True,
                    )
                    .first()
                )
                if not dep_task:
                    raise HTTPException(
                        status_code=404,
                        detail="Dependent task not found in this template",
                    )
                task.dependent_taskid = new_dep
            else:
                task.dependent_taskid = None

        if "days_offset" not in update_data and task.days_offset is None:
            task.days_offset = 0

        if "parent_id" in update_data:
            new_parent = update_data["parent_id"]
            if new_parent:
                parent = (
                    db.query(TemplateTaskMapping)
                    .filter(
                        TemplateTaskMapping.template_task_mapping_id == new_parent,
                        TemplateTaskMapping.template_id == template_id,
                        TemplateTaskMapping.is_active == True,
                    )
                    .first()
                )
                if not parent:
                    raise HTTPException(
                        status_code=404,
                        detail="Parent task not found in this template",
                    )
                task.parent_id = new_parent
            else:
                task.parent_id = None

        if "days_offset" not in update_data and task.days_offset is None:
            task.days_offset = 0

        db.commit()
        db.refresh(task)
        payload = {
            "type": "template_task_update",
            "template_id": template_id,
            "task_id": task_id,
            "task_name": task.task_name,
            "updated_by": current_user.username
        }

        if task.parent_id:  
            payload["parent_id"] = task.parent_id

        await manager.broadcast(payload)
        print(f"🔥 Broadcasted template_task_update: task_id={task_id}, parent_id={task.parent_id or 'null'}")
        return TemplateTaskOut.from_orm(task)

        
    @staticmethod
    async def delete_task(template_id: int, task_id: int, db: Session):
        # Fetch only active task
        task = (
            db.query(TemplateTaskMapping)
            .filter(
                TemplateTaskMapping.template_task_mapping_id == task_id,
                TemplateTaskMapping.template_id == template_id,
                TemplateTaskMapping.is_active == True  
            )
            .first()
        )

        if not task:
            raise HTTPException(status_code=404, detail="Task not found or already deleted")

        db.query(TemplateTaskMapping).filter(
            TemplateTaskMapping.template_task_mapping_id == task_id,
            TemplateTaskMapping.template_id == template_id
        ).update(
            {TemplateTaskMapping.is_active: False},
            synchronize_session=False
        )

        db.commit()
        payload = {
            "type": "template_task_delete",
            "template_id": template_id,
            "task_id": task_id
        }

        # ✅ Add parent_id if task had parent
        if task and task.parent_id is not None:
            payload["parent_id"] = task.parent_id

        await manager.broadcast(payload)
        print(f"🔥 Broadcasted template_task_delete: task_id={task_id}")
        return {"message": "Task soft deleted successfully"}
