from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.helpers.auth import get_current_user
from app.helpers.azure_blob import get_profile_picture_url
from app.models.user import User   
from sqlalchemy import case, func, text
from app.models.project import Project
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, Depends, Query, status
from app.models.system_constant import SystemConstant
from app.config.constant import PROJECT_STATUS_ACTIVE
from app.models.user_sorting_mapping import UserSortingMapping
from app.models.user_task_mapping import UserTaskMapping
from app.schemas.project_schema import ProjectReorderRequest
from app.models.project_task_mapping import ProjectTaskMapping
from app.models.labels_project_task_mapping import LabelsProjectTaskMapping
from app.helpers.utils import clone_template_tasks_to_project, _load_project_labels, _as_datetime
from app.schemas.project_schema import ProjectCreate, ProjectOut, ProjectUpdate, TaskOut,ProjectCopyOptions
from sqlalchemy.orm import aliased

from app.services.project_task_service import ProjectTaskService
from app.schemas.authschema import CurrentUser
from app.helpers.utils import get_project_due_bucket
from app.websockets.manager import manager


class ProjectService:
    @staticmethod
    async def create_project(payload: ProjectCreate, db: Session ,current_user: CurrentUser,):
        # user = db.query(User).filter(User.user_id == payload.user_id).first()
        # if not user:
        #     raise HTTPException(404, "User not found")

        data = payload.dict()
        data.pop("user_id", None)
        labels_payload = data.pop("labels", [])
        data["created_by"] =  current_user.username
        if "status_id" not in data or data["status_id"] is None:
            data["status_id"] = PROJECT_STATUS_ACTIVE

        max_project_sort = (
            db.query(func.max(Project.sort_order))
            .filter(Project.is_active == True)
            .scalar()
        )
        data["sort_order"] = (max_project_sort or 0) + 1

        project = Project(**data)
        db.add(project)
        db.commit()
        db.refresh(project)

        # websocket broadcast
        await manager.broadcast({
            "type": "project_create",
            "project_id": project.id,
            "project_name": project.name,
            "status_id": project.status_id
        })
        print(f"Broadcast CREATE: project {project.id}")

        for lm in payload.labels:
            max_label_sort = (
                db.query(func.max(LabelsProjectTaskMapping.sort_order))
                .filter(
                    LabelsProjectTaskMapping.project_id == project.id,
                    LabelsProjectTaskMapping.task_id == None,
                    LabelsProjectTaskMapping.is_active == True,
                )
                .scalar()
            )
            next_sort = (max_label_sort or 0) + 1
            mapping = LabelsProjectTaskMapping(
                label_id=lm.label_id,
                project_id=project.id,
                task_id=None,  
                project_label_category_id=lm.project_label_category_id,
                created_by=current_user.username,
                created_at=datetime.utcnow(),
                is_active=True,
                sort_order=next_sort,
            )
            db.add(mapping)

        db.commit()
        db.refresh(project)

        if project.template_id:
            clone_template_tasks_to_project(
                db=db,
                template_id=project.template_id,
                project_id=project.id,
                created_by=current_user.username,
            )

        proj_dict = ProjectOut.model_validate(project).model_dump()

        parent_tasks = (
            db.query(ProjectTaskMapping)
            .filter(
                ProjectTaskMapping.project_id == project.id,
                ProjectTaskMapping.parent_id == None,
                ProjectTaskMapping.is_active == True,
            )
            .all()
        )
        proj_dict["tasks"] = [TaskOut.model_validate(t).model_dump() for t in parent_tasks]

        project_labels, task_labels = _load_project_labels(db, project.id)
        proj_dict["labels"] = [l.model_dump() for l in project_labels]
        for t in proj_dict["tasks"]:
            t_id = t["id"]
            t["labels"] = [l.model_dump() for l in task_labels.get(t_id, [])]

        return proj_dict
    
    @staticmethod
    async def copy_project(payload: ProjectCopyOptions, db: Session, current_user: CurrentUser):

        if bool(payload.source_project_id) == bool(payload.source_task_id):
            raise HTTPException(400, "Provide either source_project_id or source_task_id")

        # ───────────────── BRANCH 1: COPY WHOLE PROJECT ─────────────────
        if payload.source_project_id:
            src = (
                db.query(Project)
                .options(
                    joinedload(Project.tasks)
                    .joinedload(ProjectTaskMapping.subtasks)
                )
                .filter(
                    Project.id == payload.source_project_id,
                    Project.is_active == True,
                )
                .first()
            )
            if not src:
                raise HTTPException(404, "Source project not found")
            # ✅ keep only active tasks
            src.tasks = [t for t in src.tasks if t.is_active]
            for t in src.tasks:
                t.subtasks = [st for st in t.subtasks if st.is_active]


            # user = db.query(User).filter(User.user_id == payload.user_id).first()
            # if not user:
            #     raise HTTPException(404, "User not found")

            # 1) create new project 
            if payload.copy_project:
                new_project = Project(
                    name=f"{src.name} - Copy",
                    description=src.description,
                    template_id=src.template_id,
                    start_date=_as_datetime(src.start_date),
                    end_date=_as_datetime(src.end_date),
                    status_id=src.status_id,
                    created_by=current_user.username,
                    is_active=True,
                )
            else:
                new_project = Project(
                    name=f"{src.name} - Copy",
                    description=None,
                    template_id=None,
                    start_date=None,
                    end_date=None,
                    status_id=src.status_id,
                    created_by=current_user.username,
                    is_active=True,
                )

            db.add(new_project)
            db.flush()
            max_proj_sort = (
                db.query(func.max(Project.sort_order))
                .filter(Project.is_active == True)
                .scalar()
            )
            new_project.sort_order = (max_proj_sort or 0) + 1

            # 2) if project has template, clone template tasks
            if payload.copy_project and src.template_id and not payload.copy_tasks:
                clone_template_tasks_to_project(
                    db=db,
                    template_id=src.template_id,
                    project_id=new_project.id,
                    created_by=current_user.username,
                )

            # 3) project-level labels (task_id is NULL)
            src_project_label_mappings = (
                db.query(LabelsProjectTaskMapping)
                .filter(
                    LabelsProjectTaskMapping.project_id == src.id,
                    LabelsProjectTaskMapping.task_id == None,
                    LabelsProjectTaskMapping.is_active == True,
                )
                .all()
            )

            for m in src_project_label_mappings:
                new_mapping = LabelsProjectTaskMapping(
                    label_id=m.label_id,
                    project_id=new_project.id,
                    task_id=None,
                    project_label_category_id=m.project_label_category_id,
                    created_by=current_user.username,
                    created_at=datetime.utcnow(),
                    is_active=True,
                )
                db.add(new_mapping)

            # 4) copy tasks / subtasks / task-labels
            if payload.copy_tasks:
                id_map: dict[int, int] = {}
                # 4a) parent tasks
                src_parent_tasks = [t for t in src.tasks if t.parent_id is None]

                for t in src_parent_tasks:
                    new_task = ProjectTaskMapping(
                        project_id=new_project.id,
                        task_name=t.task_name,
                        priority_id=t.priority_id,
                        is_milestone=t.is_milestone,
                        dependency_type=t.dependency_type,
                        days_offset=t.days_offset,
                        parent_id=None,
                        dependent_task_id=None,
                        start_date=_as_datetime(t.start_date) if payload.copy_subtasks else None,
                        end_date=_as_datetime(t.end_date) if payload.copy_subtasks else None,
                        status_id=t.status_id,
                        created_by=current_user.username,
                        sort_order=t.sort_order,
                        is_active=True,
                    )
                    db.add(new_task)
                    db.flush()
                    id_map[t.id] = new_task.id

                # 4b) subtasks
                if payload.copy_subtasks:
                    for t in src.tasks:
                        if t.parent_id is None:
                            continue
                        if t.parent_id not in id_map:
                            continue

                        new_task = ProjectTaskMapping(
                            project_id=new_project.id,
                            task_name=t.task_name,
                            priority_id=t.priority_id,
                            is_milestone=t.is_milestone,
                            dependency_type=t.dependency_type,
                            days_offset=t.days_offset,
                            parent_id=id_map.get(t.parent_id),
                            dependent_task_id=id_map.get(t.dependent_task_id)
                            if t.dependent_task_id in id_map
                            else None,
                            start_date=_as_datetime(t.start_date),
                            end_date=_as_datetime(t.end_date),
                            status_id=t.status_id,
                            created_by=current_user.username,
                            sort_order=t.sort_order,
                            is_active=True,
                        )
                        db.add(new_task)
                        db.flush()
                        id_map[t.id] = new_task.id

                # 4c) task-level labels
                src_task_label_mappings = (
                    db.query(LabelsProjectTaskMapping)
                    .filter(
                        LabelsProjectTaskMapping.project_id == src.id,
                        LabelsProjectTaskMapping.task_id != None,
                        LabelsProjectTaskMapping.is_active == True,
                    )
                    .all()
                )

                for m in src_task_label_mappings:
                    new_task_id = id_map.get(m.task_id)
                    if not new_task_id:
                        continue

                    new_mapping = LabelsProjectTaskMapping(
                        label_id=m.label_id,
                        project_id=new_project.id,
                        task_id=new_task_id,
                        project_label_category_id=m.project_label_category_id,
                        created_by=current_user.username,
                        created_at=datetime.utcnow(),
                        is_active=True,
                    )
                    db.add(new_mapping)

            db.commit()
            db.refresh(new_project)
            await manager.broadcast({
                "type": "project_copy",
                "new_project_id": new_project.id,
                "source_project_id": src.id,
                "project_name": new_project.name
            })
            print(f"✅ Broadcast COPY: new_project_id={new_project.id}")

            proj_dict = ProjectOut.model_validate(new_project).model_dump()
            parent_tasks = (
                db.query(ProjectTaskMapping)
                .filter(
                    ProjectTaskMapping.project_id == new_project.id,
                    ProjectTaskMapping.parent_id == None,
                    ProjectTaskMapping.is_active == True,
                )
                .all()
            )
            proj_dict["tasks"] = []

            for t in parent_tasks:
                t_dict = TaskOut.model_validate(t).model_dump()

                t_dict["subtasks"] = [
                    st for st in t_dict.get("subtasks", [])
                    if st["is_active"] is True
                ]

                proj_dict["tasks"].append(t_dict)

            project_labels, task_labels = _load_project_labels(db, new_project.id)
            proj_dict["labels"] = [l.model_dump() for l in project_labels]

            for t in proj_dict["tasks"]:
                t_id = t["id"]
                t["labels"] = [l.model_dump() for l in task_labels.get(t_id, [])]

            return proj_dict


        # ─────────────── BRANCH 2: COPY ONE TASK / SUBTASK ───────────────
        src = (
            db.query(ProjectTaskMapping)
            .options(joinedload(ProjectTaskMapping.subtasks))
            .filter(
                ProjectTaskMapping.id == payload.source_task_id,
                ProjectTaskMapping.is_active == True,
            )
            .first()
        )
        if not src:
            raise HTTPException(404, "Task not found")

        project_id = src.project_id

        # 1) copy this task in SAME project and SAME parent
        new_task = ProjectTaskMapping(
            project_id=project_id,
            task_name=f"{src.task_name} - Copy",
            priority_id=src.priority_id,
            is_milestone=src.is_milestone,
            dependency_type=src.dependency_type,
            days_offset=src.days_offset,
            parent_id=src.parent_id,      
            dependent_task_id=src.dependent_task_id,
            start_date=src.start_date,
            end_date=src.end_date,
            status_id=src.status_id,
            created_by=src.created_by,
            is_active=True,
        )
        db.add(new_task)
        db.flush()

        id_map: dict[int, int] = {src.id: new_task.id}

        # 2) copy its direct subtasks
        if payload.copy_subtasks:
            for st in src.subtasks:
                # only copy active subtasks
                if not getattr(st, 'is_active', False):
                    continue
                clone = ProjectTaskMapping(
                    project_id=project_id,
                    task_name=st.task_name,
                    priority_id=st.priority_id,
                    is_milestone=st.is_milestone,
                    dependency_type=st.dependency_type,
                    days_offset=st.days_offset,
                    parent_id=new_task.id,   
                    dependent_task_id=id_map.get(st.dependent_task_id),
                    start_date=st.start_date,
                    end_date=st.end_date,
                    status_id=st.status_id,
                    created_by=st.created_by,
                    is_active=True,
                )
                db.add(clone)
                db.flush()
                id_map[st.id] = clone.id

        # 3) copy labels for this task and its subtasks
        src_label_mappings = (
            db.query(LabelsProjectTaskMapping)
            .filter(
                LabelsProjectTaskMapping.project_id == project_id,
                LabelsProjectTaskMapping.task_id.in_(id_map.keys()),
                LabelsProjectTaskMapping.is_active == True,
            )
            .all()
        )

        for m in src_label_mappings:
            new_mapping = LabelsProjectTaskMapping(
                label_id=m.label_id,
                project_id=project_id,
                task_id=id_map[m.task_id],
                project_label_category_id=m.project_label_category_id,
                created_by = m.created_by,
                created_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(new_mapping)

        db.commit()
        db.refresh(new_task)
        # websocket broadcast
        # await manager.broadcast({
        #     "type": "task_copied",
        #     "new_task_id": new_task.id,
        #     "source_task_id": src.id,
        #     "project_id": project_id,
        #     "task_name": new_task.task_name
        # })
        # print(f"✅ Broadcast TASK COPY: new_task_id={new_task.id}")

        payload = {
            "type": "task_copied",
            "new_task_id": new_task.id,
            "source_task_id": src.id,
            "project_id": project_id,
            "task_name": new_task.task_name,
        }

        # ✅ add parent_id ONLY if source task was a subtask
        if src.parent_id is not None:
            payload["parent_id"] = new_task.parent_id

        await manager.broadcast(payload)
        print(f"✅ Broadcast TASK COPY: new_task_id={new_task.id}")

        task_with_subs = (
            db.query(ProjectTaskMapping)
            .options(joinedload(ProjectTaskMapping.subtasks))
            .filter(
                ProjectTaskMapping.id == new_task.id,
                ProjectTaskMapping.is_active == True,
            )
            .first()
        )

        result = TaskOut.model_validate(task_with_subs).model_dump()


        project_labels, task_labels = _load_project_labels(db, project_id)
        result["labels"] = [l.model_dump() for l in task_labels.get(result["id"], [])]
        for st in result["subtasks"]:
            st_id = st["id"]
            st["labels"] = [l.model_dump() for l in task_labels.get(st_id, [])]

        return result
    
    @staticmethod
    async def list_projects(
        db: Session ,
        user_id: int = None,
        assigned_user_id: int = None ,
        due_filters: Optional[List[str]] = None, current_user: CurrentUser = Depends(get_current_user),created_by: Optional[str] = None,
    ):
        sort_user_id =  current_user.user_id

        if sort_user_id is not None:
            usm = aliased(UserSortingMapping)
            rows = (
                db.query(
                    Project,
                    func.coalesce(usm.sort_order, Project.sort_order).label("effective_order")
                )
                .options(
                    joinedload(Project.tasks)
                    .joinedload(ProjectTaskMapping.subtasks)
                    .joinedload(ProjectTaskMapping.users)
                    .joinedload(UserTaskMapping.user)
                )
                .outerjoin(
                    usm,
                    (usm.project_id == Project.id)
                    & (usm.user_id == sort_user_id)
                    & (usm.is_active == True)
                )
                .filter(Project.is_active == True)
                .order_by(
                    text("effective_order"),
                    Project.id
                )
                .all()
            )

            projects = [p for (p, _) in rows]
        else:
            projects = (
                db.query(Project)
                .options(
                    joinedload(Project.tasks)
                    .joinedload(ProjectTaskMapping.subtasks)
                    .joinedload(ProjectTaskMapping.users)
                    .joinedload(UserTaskMapping.user)   # 🔥 REQUIRED
                )
                .filter(Project.is_active == True)
                .order_by(Project.sort_order, Project.id)
                .all()
            )


        # ───────── LOAD TASKS + DUE FILTER  ─────────
        if due_filters is not None and len(due_filters) > 0:
            allowed = {"late", "today", "tomorrow", "this_week", "next_week", "future", "no_date"}
            valid_filters = [f.lower() for f in due_filters if f.lower() in allowed]
            print(f"🔍 DEBUG: valid_filters = {valid_filters}")
            
            if valid_filters:
                filtered: list[Project] = []
                
                all_project_tasks = db.query(ProjectTaskMapping).filter(
                    ProjectTaskMapping.is_active == True
                ).all()
                
                matching_task_ids: set[int] = set()
                projects_with_matches: set[int] = set()
                
                for task in all_project_tasks:
                    if task.end_date is not None:
                        bucket = get_project_due_bucket(None, task.end_date)
                        print(f"🔍 TASK {task.id}: end_date={task.end_date} → BUCKET='{bucket}'")
                        if bucket in valid_filters:
                            matching_task_ids.add(task.id)
                            projects_with_matches.add(task.project_id)
                    elif "no_date" in valid_filters:
                        matching_task_ids.add(task.id)
                        projects_with_matches.add(task.project_id)
                
                print(f"🔍 Matching tasks: {len(matching_task_ids)}, Projects: {len(projects_with_matches)}")
                
                projects = [p for p in projects if p.id in projects_with_matches]

        if created_by:
                projects = [p for p in projects if p.created_by == created_by]
        assigned_task_ids: set[int] = set()

        if assigned_user_id is not None:
            assigned_task_ids_subq = (
                db.query(UserTaskMapping.task_id)
                .filter(
                    UserTaskMapping.user_id == assigned_user_id,
                    UserTaskMapping.is_active == True,
                )
                .subquery()
            )
            project_ids_with_user = {
                pid
                for (pid,) in db.query(ProjectTaskMapping.project_id)
                .filter(
                    ProjectTaskMapping.id.in_(assigned_task_ids_subq),
                    ProjectTaskMapping.is_active == True,
                )
                .distinct()
            }

            projects = [p for p in projects if p.id in project_ids_with_user]

            assigned_task_ids = {
                tid
                for (tid,) in db.query(UserTaskMapping.task_id)
                .filter(
                    UserTaskMapping.user_id == assigned_user_id,
                    UserTaskMapping.is_active == True,
                )
                .distinct()
            }
            matching_task_ids = locals().get('matching_task_ids', set())
            final_task_filter = matching_task_ids.union(assigned_task_ids)
            print(f"🔍 Final filter: {len(final_task_filter)} tasks - {final_task_filter}")
        # 3) build response
        assigned_users = (
            db.query(UserTaskMapping.task_id, User)
            .join(User, User.user_id == UserTaskMapping.user_id)  
            .filter(UserTaskMapping.is_active == True)
            .all()
        )

        assigned_user_map = {
            task_id: user for task_id, user in assigned_users
        }
        response: List[dict] = []
        for p in projects:
            creator_user = db.query(User).filter(User.username == p.created_by).first() if p.created_by else None
            proj_dict = {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "template_id": p.template_id,
                "start_date": p.start_date,
                "end_date": p.end_date,
                "status_id": p.status_id,
                "created_by": p.created_by,
                "modified_by": p.modified_by,
                "created_at": p.created_at,
                "modified_at": p.modified_at,
                "is_active": p.is_active,
                "user_id": None,
                "assigned_user_id": assigned_user_id,
                "created_by_profile_picture": creator_user.profile_picture if creator_user else None,     # ← ADD
                "created_by_profile_picture_url": get_profile_picture_url(creator_user) if creator_user else None,
                "labels": [],
                "tasks": [],
            }

            # labels
            project_labels, task_labels = _load_project_labels(db, p.id)
            proj_dict["labels"] = [l.model_dump() for l in project_labels]

            # parent tasks – filter by assigned_user_id if present
            if assigned_task_ids:
                parent_tasks: list[ProjectTaskMapping] = []
                for t in p.tasks:
                    if t.parent_id is not None:
                        continue
                    if not t.is_active:
                        continue

                    task_assigned = t.id in assigned_task_ids
                    subtask_assigned = any(
                        st.id in assigned_task_ids and st.is_active
                        for st in t.subtasks
                    )

                    if task_assigned or subtask_assigned:
                        parent_tasks.append(t)

                parent_tasks = sorted(
                    parent_tasks,
                    key=lambda t: (t.sort_order is None, t.sort_order, t.id),
                )
            else:
                parent_tasks = sorted(
                    [t for t in p.tasks if t.parent_id is None and t.is_active],
                    key=lambda t: (t.sort_order is None, t.sort_order, t.id),
                )

            # tasks + subtasks
            for pt in parent_tasks:
                t_dict = TaskOut.model_validate(pt).model_dump()
                if t_dict.get("end_date") is None:
                    t_dict["end_date"] = p.start_date
                t_dict["subtasks"] = []
                if assigned_task_ids:
                    subtasks_filtered = [
                        s
                        for s in pt.subtasks
                        if s.is_active and s.id in assigned_task_ids
                    ]
                else:
                    subtasks_filtered = [s for s in pt.subtasks if s.is_active]

                subtasks_sorted = sorted(
                    subtasks_filtered,
                    key=lambda s: (s.subtask_sort_order is None, s.subtask_sort_order, s.id),
                )
                subtasks_list = []

                for s in subtasks_sorted:
                    sub_dict = TaskOut.model_validate(s).model_dump()

                    if sub_dict.get("end_date") is None:
                        sub_dict["end_date"] = p.start_date

                    sub_dict["subtasks"] = []
                    sub_dict["users"] = [
                        {
                            "id": u.id,
                            "task_id": u.task_id,
                            "user_id": u.user_id,
                            "username": u.user.username if u.user else None,
                            "created_by": u.created_by,
                            "created_at": u.created_at,
                            "modified_by": u.modified_by,
                            "modified_at": u.modified_at,
                            "is_active": u.is_active,
                            "profile_picture": u.user.profile_picture,
                            "profile_picture_url": get_profile_picture_url(u.user),
                        }
                        for u in s.users
                        if u.is_active
                    ]
                    print(
                            f"SUBTASK {s.id} users:",
                            [(u.user_id, bool(u.user)) for u in s.users]
                        )

                    subtasks_list.append(sub_dict)

                t_dict["subtasks"] = subtasks_list


                t_id = t_dict["id"]
                t_dict["labels"] = [l.model_dump() for l in task_labels.get(t_id, [])]

                proj_dict["tasks"].append(t_dict)

            response.append(proj_dict)

        await manager.broadcast({
            "type": "projects_list_refreshed",
            # "user_id": current_user.userid,
            "project_count": len(response),
            "due_filters": due_filters or [],
            "assigned_user_id": assigned_user_id
        })
        print(f"Broadcast LIST: {len(response)} projects")

        return response
        

    
    @staticmethod
    async def get_project(project_id: int, db: Session, current_user: CurrentUser):
        project = (
            db.query(Project)
            .options(
                joinedload(Project.tasks)
                .joinedload(ProjectTaskMapping.subtasks)
                .joinedload(ProjectTaskMapping.users)
            )
            .filter(Project.id == project_id, Project.is_active == True)
            .first()
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        proj_dict = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "template_id": project.template_id,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "status_id": project.status_id,
            "created_by": project.created_by,
            "modified_by": project.modified_by,
            "created_at": project.created_at,
            "modified_at": project.modified_at,
            "is_active": project.is_active,
            "user_id": current_user.user_id,
            "sort_order": project.sort_order,

            "labels": [],
            "tasks": [],
        }

        parent_tasks = [t for t in project.tasks if t.parent_id is None]

        project_labels, task_labels = _load_project_labels(db, project_id)
        proj_dict["labels"] = [l.model_dump() for l in project_labels]

        for pt in parent_tasks:
            t_dict = TaskOut.model_validate(pt).model_dump()
            if t_dict.get("end_date") is None:
                t_dict["end_date"] = project.start_date
            t_dict["subtasks"] = []

            subtasks_sorted = sorted(
                pt.subtasks,
                key=lambda s: (s.subtask_sort_order is None, s.subtask_sort_order, s.id),
            )
            subtasks_list = []

            for s in subtasks_sorted:
                sub_dict = TaskOut.model_validate(s).model_dump()

                if sub_dict.get("end_date") is None:
                    sub_dict["end_date"] = project.start_date

                sub_dict["subtasks"] = []

                subtasks_list.append(sub_dict)

            t_dict["subtasks"] = subtasks_list


            t_id = t_dict["id"]
            t_dict["labels"] = [l.model_dump() for l in task_labels.get(t_id, [])]

            proj_dict["tasks"].append(t_dict)

        await manager.broadcast({
            "type": "project_viewed",
            "project_id": project_id,
            "project_name": project.name,
            "user_id": current_user.user_id
        })
        print(f"Broadcast VIEW: project {project_id}")

        return proj_dict
    
    @staticmethod
    def reorder_projects(
        payload: ProjectReorderRequest,
        db: Session,
        current_user: CurrentUser,
):
        positions = payload.items
        user_id = current_user.user_id

        if not positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reorder payload",
            )

        project_items = [p for p in positions if p.project_id is not None and p.task_id is None]
        task_items    = [p for p in positions if p.task_id is not None and p.parent_task_id is None]
        subtask_items = [p for p in positions if p.task_id is not None and p.parent_task_id is not None]

        # ───────────── PROJECT REORDER ─────────────
        if project_items:
            proj_ids = [p.project_id for p in project_items]

            projects = (
                db.query(Project)
                .filter(
                    Project.id.in_(proj_ids),
                    Project.is_active == True,
                )
                .all()
            )
            valid_ids = {p.id for p in projects}
            for pid in proj_ids:
                if pid not in valid_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid project id in reorder payload",
                    )

            if user_id is not None:
                existing = (
                    db.query(UserSortingMapping)
                    .filter(
                        UserSortingMapping.user_id == user_id,
                        UserSortingMapping.project_id.in_(proj_ids),
                        UserSortingMapping.is_active == True,
                    )
                    .all()
                )
                by_pid = {m.project_id: m for m in existing}

                for item in project_items:
                    row = by_pid.get(item.project_id)
                    if not row:
                        row = UserSortingMapping(
                            user_id=user_id,
                            project_id=item.project_id,
                            is_active=True,
                        )
                        db.add(row)
                    row.sort_order = item.position    
            else:
                projects_by_id = {p.id: p for p in projects}
                for item in project_items:
                    proj = projects_by_id[item.project_id]
                    proj.sort_order = item.position   
        # ───────────── TASK REORDER (within project) ─────────────
        if task_items:
            task_ids = [p.task_id for p in task_items]

            tasks = (
                db.query(ProjectTaskMapping)
                    .filter(
                        ProjectTaskMapping.id.in_(task_ids),
                        ProjectTaskMapping.is_active == True,
                        ProjectTaskMapping.parent_id == None,  
                    )
                    .all()
            )
            valid_task_ids = {t.id for t in tasks}

            for tid in task_ids:
                if tid not in valid_task_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid task id in reorder payload",
                    )

            tasks_by_id = {t.id: t for t in tasks}
            for item in task_items:
                task = tasks_by_id[item.task_id]
                task.sort_order = item.position

        # ───────────── SUBTASK REORDER  ─────────────
        if subtask_items:
            subtask_ids = [p.task_id for p in subtask_items]
            parent_ids  = {p.parent_task_id for p in subtask_items}

            if len(parent_ids) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Subtask reorder must be within a single parent task",
                )
            parent_id = next(iter(parent_ids))

            subtasks = (
                db.query(ProjectTaskMapping)
                    .filter(
                        ProjectTaskMapping.id.in_(subtask_ids),
                        ProjectTaskMapping.is_active == True,
                        ProjectTaskMapping.parent_id == parent_id,
                    )
                    .all()
            )
            valid_sub_ids = {t.id for t in subtasks}

            for tid in subtask_ids:
                if tid not in valid_sub_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid subtask id in reorder payload",
                    )
            subtasks_by_id = {t.id: t for t in subtasks}
            for item in subtask_items:
                st = subtasks_by_id[item.task_id]
                st.subtask_sort_order = item.position

        db.commit()
        return None
    
    @staticmethod
    async def update_project(project_id: int, payload: ProjectUpdate, db: Session ,current_user: CurrentUser):
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")

        update_data = payload.dict(exclude_unset=True)
        new_status_id = update_data.get("status_id")

        if new_status_id is not None:
            status_row = db.query(SystemConstant).filter(
                SystemConstant.id == new_status_id,
                SystemConstant.type == "PROJECT_STATUS",
                SystemConstant.is_active == True,
            ).first()

            if not status_row:
                update_data["status_id"] = PROJECT_STATUS_ACTIVE
        else:
            update_data["status_id"] = project.status_id or PROJECT_STATUS_ACTIVE

        for key, value in update_data.items():
            setattr(project, key, value)

        project.modified_by = current_user.username

        db.commit()
        db.refresh(project)

        await manager.broadcast({
            "type": "project_update", 
            "project_id": project.id,
            "project_name": project.name,
            "status_id": project.status_id
        })
        print(f"Broadcast UPDATE: project {project.id}")
        if payload.start_date is not None:
            ProjectTaskService.recompute_project_schedule(project.id, db)
        return project
    
    @staticmethod
    async def delete_project(project_id: int, db: Session = Depends(get_db)):
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.is_active == True)
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.project_id == project_id
        ).update(
            {ProjectTaskMapping.dependent_task_id: None},
            synchronize_session=False,
        )

        db.query(UserTaskMapping).filter(
            UserTaskMapping.task_id.in_(
                db.query(ProjectTaskMapping.id).filter(
                    ProjectTaskMapping.project_id == project_id
                )
            )
        ).update(
            {UserTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(LabelsProjectTaskMapping).filter(
            LabelsProjectTaskMapping.project_id == project_id
        ).update(
            {LabelsProjectTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(ProjectTaskMapping).filter(
            ProjectTaskMapping.project_id == project_id
        ).update(
            {ProjectTaskMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(UserSortingMapping).filter(
            UserSortingMapping.project_id == project_id
        ).update(
            {UserSortingMapping.is_active: False},  
            synchronize_session=False,
        )

        db.query(Project).filter(
            Project.id == project_id
        ).update(
            {Project.is_active: False}, 
            synchronize_session=False,
        )

        db.commit()
        await manager.broadcast({
            "type": "project_delete",
            "project_id": project_id,
            "project_name": project.name  # Save before update
        })
        print(f"Broadcast DELETE: project {project_id}")
        return {"message": "Project soft deleted successfully"}
