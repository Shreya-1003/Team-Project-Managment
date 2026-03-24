# app/routes/project_routes.py
from datetime import timedelta
from sqlalchemy import func
from app.database import get_db
from app.models.labels_project_task_mapping import LabelsProjectTaskMapping
from app.models.user import User   
from sqlalchemy.orm import joinedload
from app.models.project import Project
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from app.models.project_task_mapping import ProjectTaskMapping
from app.schemas.project_schema import TaskCreate, TaskOut, TaskUpdate
from app.models.system_constant import SystemConstant
from app.models.user_task_mapping import UserTaskMapping
from app.config.constant import (
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_MEDIUM,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_CRITICAL,
    TASK_STATUS,
    DEPENDENCY_TYPE,
)
from app.helpers.utils import _get_dependency_type_ids, _add_workdays,recompute_schedule_for_tasks
from app.schemas.authschema import CurrentUser
from app.websockets.manager import manager

def update_dependent_tasks(db: Session, parent_task):
    """
    Recursively update all tasks that depend on parent_task.
    This considers each task's days_offset and dependency_type.
    """
    dep_ids = _get_dependency_type_ids(db)
    before_id = dep_ids.get("Before")
    after_id = dep_ids.get("After")

    # Find all tasks that depend on this parent task
    dependents = db.query(ProjectTaskMapping).filter(
        ProjectTaskMapping.dependent_task_id == parent_task.id,
        ProjectTaskMapping.is_active == True
    ).all()

    for task in dependents:
        offset = task.days_offset or 0
        base_date = parent_task.start_date

        if not base_date:
            continue

        # Calculate new start_date based on dependency type and offset
        if task.dependency_type == after_id:
            task.start_date = _add_workdays(base_date, offset)
        elif task.dependency_type == before_id:
            task.start_date = _add_workdays(base_date, -offset)
        else:
            task.start_date = base_date

        # For simplicity, keep end_date = start_date; you can extend for duration
        task.end_date = task.start_date

        # Commit and refresh each task
        db.commit()
        db.refresh(task)

        # 🔁 Recursively update downstream tasks
        update_dependent_tasks(db, task)

class ProjectTaskService:

    @staticmethod
    def recompute_project_schedule(project_id: int, db: Session = Depends(get_db)):
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.start_date:
            return

        tasks = db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.project_id == project_id,
            ProjectTaskMapping.is_active == True,
        ).all()

        recompute_schedule_for_tasks(db, project.start_date, tasks)

    @staticmethod
    async def create_task(project_id: int, payload: TaskCreate, db: Session,current_user: CurrentUser,):
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        data = payload.dict()
        user_ids = data.pop("user_ids", [])
        data.pop("created_by_user_id", None)

        data["project_id"] = project_id
        data["status_id"] = data.get("status_id", TASK_STATUS)
        data["created_by"] = current_user.username

        # ----- priority from SystemConstant -----
        raw_priority = payload.priority_id

        if raw_priority is None:
            priority_id = TASK_PRIORITY_HIGH
        else:
            if isinstance(raw_priority, int):
                priority_id = raw_priority
            else:
                pr_row = (
                    db.query(SystemConstant)
                    .filter(
                        SystemConstant.id.in_(
                            [
                                TASK_PRIORITY_LOW,
                                TASK_PRIORITY_MEDIUM,
                                TASK_PRIORITY_HIGH,
                                TASK_PRIORITY_CRITICAL,
                            ]
                        ),
                        SystemConstant.name == raw_priority,
                        SystemConstant.is_active == True,
                    )
                    .first()
                )
                if not pr_row:
                    raise HTTPException(status_code=400, detail="Invalid priority")
                priority_id = pr_row.id

        data["priority_id"] = priority_id

        # ----- dependency_type  -----
        dep_type_val = data.get("dependency_type")

        if dep_type_val is None:
            data["dependency_type"] = None
        else:
            # if isinstance(dep_type_val, int):
            #     data["dependency_type"] = dep_type_val
            if isinstance(dep_type_val, int):
                dep_row = (
                    db.query(SystemConstant)
                    .filter(
                        SystemConstant.id == dep_type_val,
                        SystemConstant.is_active == True,
                    )
                    .first()
                )
                if not dep_row:
                    raise HTTPException(status_code=400, detail="Invalid dependency type")
                data["dependency_type"] = dep_row.id

            else:
                parent = (
                    db.query(SystemConstant)
                    .filter(
                        SystemConstant.id == DEPENDENCY_TYPE,
                        SystemConstant.is_active == True,
                    )
                    .first()
                )
                if not parent:
                    raise HTTPException(status_code=400, detail="Dependency type root not found")

                dep_row = (
                    db.query(SystemConstant)
                    .filter(
                        SystemConstant.type == parent.type,
                        SystemConstant.name == dep_type_val,
                        SystemConstant.is_active == True,
                    )
                    .first()
                )
                if not dep_row:
                    raise HTTPException(status_code=400, detail="Invalid dependency type")

                data["dependency_type"] = dep_row.id

        depends_on = data.pop("depends_on", None)

        # if depends_on:
        #     data["dependent_task_id"] = depends_on
        # else:
        #     data["dependent_task_id"] = None
        if depends_on:
            dep_task = (
                db.query(ProjectTaskMapping)
                .filter(
                    ProjectTaskMapping.id == depends_on,
                    ProjectTaskMapping.project_id == project_id,
                    ProjectTaskMapping.is_active == True
                )
                .first()
            )

            if not dep_task:
                raise HTTPException(
                    status_code=400,
                    detail="Dependent task does not exist in this project"
                )

            data["dependent_task_id"] = dep_task.id
        else:
            data["dependent_task_id"] = None


        if data.get("days_offset") is None:
            data["days_offset"] = 0

        base_date = project.start_date
        if base_date is not None and hasattr(base_date, "date"):
            base_date = base_date.date()

        start_date = data.get("start_date")
        final_due_date = data.get("end_date")

        if base_date is not None:
            if data.get("dependent_task_id") is None:
                final_due_date = final_due_date or base_date
            else:
                dep_task = (
                    db.query(ProjectTaskMapping)
                    .filter(ProjectTaskMapping.id == data["dependent_task_id"])
                    .first()
                )

                if dep_task and dep_task.start_date:
                    dep_date = dep_task.start_date   # ✅ ONLY CHANGE
                    if hasattr(dep_date, "date"):
                        dep_date = dep_date.date()

                    dep_ids = _get_dependency_type_ids(db)
                    before_id = dep_ids.get("Before")
                    after_id = dep_ids.get("After")

                    offset = data["days_offset"] or 0

                    if data["dependency_type"] == after_id:
                        final_due_date = _add_workdays(dep_date, offset)
                    elif data["dependency_type"] == before_id:
                        final_due_date = _add_workdays(dep_date, -offset)
                    else:
                        final_due_date = dep_date


        # data["start_date"] = start_date
        data["end_date"] = final_due_date
        data["start_date"] = final_due_date
        if data.get("end_date") is None:
            if project.start_date:
                data["end_date"] = project.start_date
        # ----- parent / days_offset (existing) -----
        if data.get("parent_id"):
            parent = (
                db.query(ProjectTaskMapping)
                .filter(ProjectTaskMapping.id == data["parent_id"])
                .first()
            )
            if parent and parent.start_date and data.get("start_date"):
                if data.get("days_offset") is None:
                    child_date = data["start_date"]
                    parent_date = parent.start_date
                    if hasattr(child_date, "date"):
                        child_date = child_date.date()
                    if hasattr(parent_date, "date"):
                        parent_date = parent_date.date()
                    data["days_offset"] = (child_date - parent_date).days
            else:
                if data.get("days_offset") is None:
                    data["days_offset"] = 0

        # ----- sort order (existing) -----
        if data.get("parent_id"):
            max_sort = (
                db.query(func.max(ProjectTaskMapping.sort_order))
                .filter(
                    ProjectTaskMapping.project_id == project_id,
                    ProjectTaskMapping.parent_id == data["parent_id"],
                    ProjectTaskMapping.is_active == True,
                )
                .scalar()
            )
        else:
            max_sort = (
                db.query(func.max(ProjectTaskMapping.sort_order))
                .filter(
                    ProjectTaskMapping.project_id == project_id,
                    ProjectTaskMapping.parent_id == None,
                    ProjectTaskMapping.is_active == True,
                )
                .scalar()
            )

        data["sort_order"] = (max_sort or 0) + 1

        task = ProjectTaskMapping(**data)
        db.add(task)
        db.flush()

        mappings = []
        if data.get("parent_id") and user_ids:
            users = (
                db.query(User)
                .filter(User.user_id.in_(user_ids), User.is_active == True)
                .all()
            )
            if len(users) != len(set(user_ids)):
                raise HTTPException(
                    status_code=400,
                    detail="One or more assigned users not found",
                )

            mappings = []
            for u in users:
                mapping = UserTaskMapping(
                    task_id=task.id,
                    user_id=u.user_id,
                    created_by=current_user.username,
                    is_active=True,
                )
                db.add(mapping)
                mappings.append(mapping)

        if mappings:
            task.users.extend(mappings)

        db.commit()
        db.refresh(task)
        ProjectTaskService.recompute_project_schedule(project_id, db)
        # WebSocket Broadcast - CREATE
        try:
            await manager.broadcast({
                "type": "project_task_create",
                "task_id": task.id,
                "project_id": project_id,
                "task_name": task.task_name,
                "status_id": task.status_id,
                "parent_id": task.parent_id
                
            })
            print(f"Broadcast CREATE: project task {task.id}")
        except Exception as e:
            print(f"WS Broadcast failed (CREATE): {e}")
        return TaskOut.from_orm(task)
    
    @staticmethod
    def list_tasks(project_id: int, db: Session = Depends(get_db)):
        tasks = (
            db.query(ProjectTaskMapping)
            .options(
                joinedload(ProjectTaskMapping.subtasks),
                joinedload(ProjectTaskMapping.users),
            )
            .filter(
                ProjectTaskMapping.project_id == project_id,
                ProjectTaskMapping.is_active == True,
            )
            .order_by(ProjectTaskMapping.sort_order.asc())
            .all()
        )

        result: list[TaskOut] = []
        for t in tasks:
            subtasks_simple = [
                {
                    "id": st.id,
                    "task_name": st.task_name,
                    "project_id": st.project_id,
                    "created_at": st.created_at,
                    "modified_at": st.modified_at,
                    "is_active": st.is_active,
                    "status_id": st.status_id,
                    "priority_id": st.priority_id,
                    "dependency_type": st.dependency_type,
                    "dependent_task_id": st.dependent_task_id,
                    "days_offset": st.days_offset,
                    "depends_on": None,
                    "sort_order": st.sort_order,
                    "subtask_sort_order": st.subtask_sort_order,
                    "start_date": st.start_date,     
                    "end_date": st.end_date,
                    "subtasks": [],
                    "users": [],
                }
                for st in t.subtasks
                if st.is_active
            ]

            task_out = TaskOut(
                id=t.id,
                task_name=t.task_name,
                project_id=t.project_id,
                created_at=t.created_at,
                modified_at=t.modified_at,
                is_active=t.is_active,
                status_id=t.status_id,
                priority_id=t.priority_id,
                dependency_type=t.dependency_type,
                dependent_task_id=t.dependent_task_id,
                days_offset=t.days_offset,
                depends_on=None,
                sort_order=t.sort_order,
                subtask_sort_order=t.subtask_sort_order,
                start_date=t.start_date,          
                end_date=t.end_date,
                subtasks=subtasks_simple,
                users=[],  
            )
            result.append(task_out)

        return result
        
    # @staticmethod
    # async def update_task(project_id: int, task_id: int, payload: TaskUpdate, db: Session ,current_user: CurrentUser):
    #     task = db.query(ProjectTaskMapping).options(
    #         joinedload(ProjectTaskMapping.subtasks),
    #         joinedload(ProjectTaskMapping.users)
    #     ).filter(
    #         ProjectTaskMapping.id == task_id,
    #         ProjectTaskMapping.project_id == project_id
    #     ).first()

    #     if not task:
    #         raise HTTPException(404, "Task not found")

    #     update_data = payload.dict(exclude_unset=True)
    #     update_data.pop("modified_by_user_id", None)
    #     update_data.pop("created_by_user_id", None)
    #     update_data.pop("created_by", None)
    #     update_data.pop("modified_by", None)

    #     # set modified_by from token
    #     task.modified_by = current_user.username
    #     if "priority_id" not in update_data:
    #         update_data["priority_id"] = task.priority_id or TASK_PRIORITY_HIGH

    #     if "status_id" not in update_data:
    #         update_data["status_id"] = task.status_id or TASK_STATUS

    #     for key, value in update_data.items():
    #         setattr(task, key, value)

    #     if "depends_on" in update_data:
    #         new_dep = update_data["depends_on"]
    #         task.dependent_task_id = new_dep
    #         if new_dep:
    #             dep_task = db.query(ProjectTaskMapping).filter(
    #                 ProjectTaskMapping.id == new_dep
    #             ).first()

    #             if dep_task and dep_task.start_date and task.start_date:
    #                 if "days_offset" not in update_data:
    #                     task.days_offset = (task.start_date - dep_task.start_date).days
    #             else:
    #                 if "days_offset" not in update_data:
    #                     task.days_offset = 0
    #         else:
    #             if "days_offset" not in update_data:
    #                 task.days_offset = 0

    #     if "parent_id" in update_data:
    #         new_parent_id = update_data["parent_id"]
    #         if new_parent_id == task.id:
    #             raise HTTPException(400, "Task cannot be its own parent")

    #         if new_parent_id:
    #             new_parent = db.query(ProjectTaskMapping).filter(
    #                 ProjectTaskMapping.id == new_parent_id,
    #                 ProjectTaskMapping.project_id == project_id
    #             ).first()
    #             if not new_parent:
    #                 raise HTTPException(400, "Parent task not found in this project")

    #             if any(st.id == new_parent_id for st in task.subtasks):
    #                 raise HTTPException(400, "Cannot set a subtask as parent task")
    #             if new_parent.start_date and task.start_date and "days_offset" not in update_data:
    #                 task.days_offset = (task.start_date - new_parent.start_date).days
    #         task.parent_id = new_parent_id

    #     if task.days_offset is None:
    #         task.days_offset = 0

    #     project = db.query(Project).filter(Project.id == project_id).first()
    #     base_date = project.start_date if project else None
    #     if base_date is not None and hasattr(base_date, "date"):
    #         base_date = base_date.date()

    #     if base_date is not None:
    #         dep_ids = _get_dependency_type_ids(db)  
    #         before_id = dep_ids.get("Before")
    #         after_id = dep_ids.get("After")

    #         if task.dependent_task_id is None:
    #             task.start_date = base_date
    #         else:
    #             dep_task = db.query(ProjectTaskMapping).filter(
    #                 ProjectTaskMapping.id == task.dependent_task_id
    #             ).first()
    #             if dep_task and dep_task.start_date:
    #                 dep_date = dep_task.start_date
    #                 if hasattr(dep_date, "date"):
    #                     dep_date = dep_date.date()

    #                 offset = task.days_offset or 0
    #                 if task.dependency_type == after_id:
    #                     task.start_date = dep_date + timedelta(days=offset)
    #                 elif task.dependency_type == before_id:
    #                     task.start_date = dep_date - timedelta(days=offset)
    #                 else:
    #                     task.start_date = base_date + timedelta(days=offset)

    #     if "user_ids" in update_data and task.parent_id:
    #         new_user_ids = set(update_data["user_ids"] or [])

    #         existing_mappings = db.query(UserTaskMapping).filter(
    #             UserTaskMapping.task_id == task.id
    #         ).all()
    #         existing_by_user = {m.user_id: m for m in existing_mappings}

    #         if new_user_ids:
    #             users = db.query(User).filter(
    #                 User.user_id.in_(new_user_ids),
    #                 User.is_active == True,
    #             ).all()
    #             if len(users) != len(new_user_ids):
    #                 raise HTTPException(
    #                     status_code=400,
    #                     detail="One or more assigned users not found",
    #                 )
    #         for uid in new_user_ids:
    #             mapping = existing_by_user.get(uid)
    #             if mapping:
    #                 mapping.is_active = True        
    #             else:
    #                 mapping = UserTaskMapping(
    #                     task_id=task.id,
    #                     user_id=uid,
    #                     created_by=current_user.username if current_user else task.created_by,
    #                     is_active=True,
    #                 )
    #                 db.add(mapping)

    #         for uid, mapping in existing_by_user.items():
    #             if uid not in new_user_ids:
    #                 mapping.is_active = False

    #         if task.end_date is None:
    #             project = db.query(Project).filter(Project.id == project_id).first()
    #             if project and project.start_date:
    #                 task.end_date = project.start_date
    #     db.commit()
    #     db.refresh(task, ['subtasks', 'users'])
    #     # task.subtasks = []
    #     subtasks_query = db.query(ProjectTaskMapping).filter(
    #         ProjectTaskMapping.parent_id == task_id,
    #         ProjectTaskMapping.is_active == True
    #     ).options(
    #         joinedload(ProjectTaskMapping.users)
    #     ).all()
    #     task.subtasks = subtasks_query
        
    #     subtasks_simple = []
    #     for st in task.subtasks:
    # # Recursively load subtask users
    #         st_users = []
    #         if hasattr(st, 'users'):
    #             for u in st.users:
    #                 if getattr(u, 'is_active', False):
    #                     st_users.append({
    #                         "id": u.id,
    #                         "user_id": u.user_id,
    #                         "task_id": u.task_id,
    #                         "created_by": u.created_by,
    #                         "created_at": u.created_at,
    #                         "modified_by": u.modified_by,
    #                         "modified_at": u.modified_at,
    #                         "is_active": u.is_active
    #                     })
            
    #         subtasks_simple.append({
    #             "id": st.id,
    #             "task_name": st.task_name,
    #             "project_id": st.project_id,
    #             "created_at": st.created_at,
    #             "modified_at": st.modified_at,
    #             "is_active": st.is_active,
    #             "status_id": st.status_id,
    #             "priority_id": st.priority_id,
    #             "dependency_type": st.dependency_type,
    #             "dependent_task_id": st.dependent_task_id,
    #             "days_offset": st.days_offset,
    #             "depends_on": None,
    #             "sort_order": getattr(st, 'sort_order', None),
    #             "subtask_sort_order": getattr(st, 'subtask_sort_order', None),
    #             "start_date": st.start_date,
    #             "end_date": st.end_date,
    #             "subtasks": [],
    #             "users": st_users,
    #             "labels": []
    #         })
    
    #     # WebSocket Broadcast - UPDATE
    #     try:
    #         await manager.broadcast({
    #             "type": "project_task_update",
    #             "task_id": task_id,
    #             "project_id": project_id,
    #             "status_id": task.status_id,
    #             "task_name": task.task_name,
    #             "parent_id": task.parent_id
    #         })
    #         print(f"Broadcast UPDATE: project task {task_id}")
    #     except Exception as e:
    #         print(f"WS Broadcast failed (UPDATE): {e}")
    #     # if hasattr(task, "users"):
    #     #     task.users = [u for u in task.users if getattr(u, "is_active", False)]
    #     return TaskOut(
    #         id=task.id,
    #         task_name=task.task_name,
    #         project_id=task.project_id,
    #         created_at=task.created_at,
    #         modified_at=task.modified_at,
    #         is_active=task.is_active,
    #         status_id=task.status_id,
    #         priority_id=task.priority_id,
    #         dependency_type=task.dependency_type,
    #         dependent_task_id=task.dependent_task_id,
    #         days_offset=task.days_offset,
    #         depends_on=None,
    #         sort_order=task.sort_order,
    #         subtask_sort_order=task.subtask_sort_order,
    #         start_date=task.start_date,
    #         end_date=task.end_date,
    #         subtasks=subtasks_simple,
    #         users=[]
    #     )

    @staticmethod
    async def update_task(
        project_id: int,
        task_id: int,
        payload: TaskUpdate,
        db: Session,
        current_user: CurrentUser
    ):
        # --- Fetch task ---
        task = db.query(ProjectTaskMapping).options(
            joinedload(ProjectTaskMapping.subtasks),
            joinedload(ProjectTaskMapping.users)
        ).filter(
            ProjectTaskMapping.id == task_id,
            ProjectTaskMapping.project_id == project_id
        ).first()

        if not task:
            raise HTTPException(404, "Task not found")

        update_data = payload.dict(exclude_unset=True)
        update_data.pop("modified_by_user_id", None)
        update_data.pop("created_by_user_id", None)
        update_data.pop("created_by", None)
        update_data.pop("modified_by", None)

        # Detect date / dependency change
        recompute_fields = {
            "start_date", "end_date", "days_offset",
            "dependency_type", "dependent_task_id", "depends_on"
        }
        should_recompute = any(field in update_data for field in recompute_fields)

        # --- Set modified_by ---
        task.modified_by = current_user.username

        # --- Default priority/status ---
        if "priority_id" not in update_data:
            update_data["priority_id"] = task.priority_id or TASK_PRIORITY_HIGH
        if "status_id" not in update_data:
            update_data["status_id"] = task.status_id or TASK_STATUS

        # --- Apply updates ---
        for key, value in update_data.items():
            setattr(task, key, value)

        # --- Handle depends_on ---
        if "depends_on" in update_data:
            new_dep = update_data["depends_on"]
            task.dependent_task_id = new_dep
            if new_dep:
                dep_task = db.query(ProjectTaskMapping).filter(
                    ProjectTaskMapping.id == new_dep
                ).first()
                if dep_task and dep_task.start_date and task.start_date:
                    if "days_offset" not in update_data:
                        task.days_offset = (task.start_date - dep_task.start_date).days
                else:
                    if "days_offset" not in update_data:
                        task.days_offset = 0
            else:
                if "days_offset" not in update_data:
                    task.days_offset = 0

        # --- Handle parent_id ---
        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id == task.id:
                raise HTTPException(400, "Task cannot be its own parent")

            if new_parent_id:
                new_parent = db.query(ProjectTaskMapping).filter(
                    ProjectTaskMapping.id == new_parent_id,
                    ProjectTaskMapping.project_id == project_id
                ).first()
                if not new_parent:
                    raise HTTPException(400, "Parent task not found in this project")

                if any(st.id == new_parent_id for st in task.subtasks):
                    raise HTTPException(400, "Cannot set a subtask as parent task")

                if new_parent.start_date and task.start_date and "days_offset" not in update_data:
                    task.days_offset = (task.start_date - new_parent.start_date).days

            task.parent_id = new_parent_id

        if task.days_offset is None:
            task.days_offset = 0

        # --- Fetch project base date ---
        project = db.query(Project).filter(Project.id == project_id).first()
        base_date = project.start_date if project else None
        if base_date is not None and hasattr(base_date, "date"):
            base_date = base_date.date()

        # --- Calculate task dates ---
        dep_ids = _get_dependency_type_ids(db)
        before_id = dep_ids.get("Before")
        after_id = dep_ids.get("After")

        if task.dependent_task_id:
            dep_task = db.query(ProjectTaskMapping).filter(
                ProjectTaskMapping.id == task.dependent_task_id
            ).first()
            if dep_task and dep_task.start_date:
                dep_date = dep_task.start_date
                if hasattr(dep_date, "date"):
                    dep_date = dep_date.date()
                offset = task.days_offset or 0
                if task.dependency_type == after_id:
                    task.start_date = _add_workdays(dep_date, offset)
                    task.end_date = task.start_date
                elif task.dependency_type == before_id:
                    task.start_date = _add_workdays(dep_date, -offset)
                    task.end_date = task.start_date
                else:
                    task.start_date = task.start_date or base_date
        else:
            # Respect user-provided start_date
            task.start_date = task.start_date or base_date

        # --- User assignment logic (unchanged) ---
        if "user_ids" in update_data and task.parent_id:
            new_user_ids = set(update_data["user_ids"] or [])
            existing_mappings = db.query(UserTaskMapping).filter(
                UserTaskMapping.task_id == task.id
            ).all()
            existing_by_user = {m.user_id: m for m in existing_mappings}

            if new_user_ids:
                users = db.query(User).filter(
                    User.user_id.in_(new_user_ids),
                    User.is_active == True,
                ).all()
                if len(users) != len(new_user_ids):
                    raise HTTPException(400, "One or more assigned users not found")

            for uid in new_user_ids:
                mapping = existing_by_user.get(uid)
                if mapping:
                    mapping.is_active = True
                else:
                    mapping = UserTaskMapping(
                        task_id=task.id,
                        user_id=uid,
                        created_by=current_user.username if current_user else task.created_by,
                        is_active=True,
                    )
                    db.add(mapping)

            for uid, mapping in existing_by_user.items():
                if uid not in new_user_ids:
                    mapping.is_active = False

        # --- First commit ---
        db.commit()
        db.refresh(task)

        # --- Cascade update dependent tasks ---
        update_dependent_tasks(db, task)

        # --- Refresh task again after cascade ---
        db.refresh(task)

        # --- Subtasks response ---
        subtasks_query = db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.parent_id == task_id,
            ProjectTaskMapping.is_active == True
        ).options(joinedload(ProjectTaskMapping.users)).all()
        task.subtasks = subtasks_query

        subtasks_simple = []
        for st in task.subtasks:
            st_users = [
                {
                    "id": u.id,
                    "user_id": u.user_id,
                    "task_id": u.task_id,
                    "created_by": u.created_by,
                    "created_at": u.created_at,
                    "modified_by": u.modified_by,
                    "modified_at": u.modified_at,
                    "is_active": u.is_active
                }
                for u in getattr(st, 'users', []) if getattr(u, 'is_active', False)
            ]

            subtasks_simple.append({
                "id": st.id,
                "task_name": st.task_name,
                "project_id": st.project_id,
                "created_at": st.created_at,
                "modified_at": st.modified_at,
                "is_active": st.is_active,
                "status_id": st.status_id,
                "priority_id": st.priority_id,
                "dependency_type": st.dependency_type,
                "dependent_task_id": st.dependent_task_id,
                "days_offset": st.days_offset,
                "depends_on": None,
                "sort_order": getattr(st, 'sort_order', None),
                "subtask_sort_order": getattr(st, 'subtask_sort_order', None),
                "start_date": st.start_date,
                "end_date": st.end_date,
                "subtasks": [],
                "users": st_users,
                "labels": []
            })

        # --- WebSocket Broadcast ---
        try:
            await manager.broadcast({
                "type": "project_task_update",
                "task_id": task_id,
                "project_id": project_id,
                "status_id": task.status_id,
                "task_name": task.task_name,
                "parent_id": task.parent_id
            })
        except Exception as e:
            print(f"WS Broadcast failed (UPDATE): {e}")

        return TaskOut(
            id=task.id,
            task_name=task.task_name,
            project_id=task.project_id,
            created_at=task.created_at,
            modified_at=task.modified_at,
            is_active=task.is_active,
            status_id=task.status_id,
            priority_id=task.priority_id,
            dependency_type=task.dependency_type,
            dependent_task_id=task.dependent_task_id,
            days_offset=task.days_offset,
            depends_on=None,
            sort_order=task.sort_order,
            subtask_sort_order=task.subtask_sort_order,
            start_date=task.start_date,
            end_date=task.end_date,
            subtasks=subtasks_simple,
            users=[]
        )


    @staticmethod
    async def delete_task(task_id: int, db: Session ,project_id: int):
        task = (
            db.query(ProjectTaskMapping)
            .filter(ProjectTaskMapping.id == task_id,ProjectTaskMapping.is_active == True)
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.dependent_task_id == task_id
        ).update(
            {ProjectTaskMapping.dependent_task_id: None},
            synchronize_session=False,
        )

        db.query(LabelsProjectTaskMapping).filter(
            LabelsProjectTaskMapping.task_id == task_id
        ).update(
            {LabelsProjectTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(UserTaskMapping).filter(
            UserTaskMapping.task_id == task_id
        ).update(
            {UserTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.parent_id == task_id
        ).update(
            {ProjectTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.id == task_id
        ).update(
            {ProjectTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.commit()

        try:
            await manager.broadcast({
                "type": "project_task_delete",
                "task_id": task_id,
                "project_id": project_id,
                "task_name": task.task_name,
                "parent_id": task.parent_id
            })
            print(f"Broadcast DELETE: project task {task_id}")
        except Exception as e:
            print(f"WS Broadcast failed (DELETE): {e}")
        return
