from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.template import Template
from app.models.template_task_mapping import TemplateTaskMapping
from app.schemas.authschema import CurrentUser
from app.schemas.template_schema import TemplateCreate, TemplateOut, TemplateReorderRequest, TemplateUpdate, TemplateTaskCreate, TemplateTaskOut, TemplateTaskUpdate,TemplateCopyOptions
from app.models.user import User  
from sqlalchemy import case,func
from app.config.constant import TASK_PRIORITY_HIGH, TASK_STATUS, DEPENDENCY_TYPE
from app.models.system_constant import SystemConstant
from datetime import datetime
from app.websockets.manager import manager

class TemplateService:
    @staticmethod
    async def create_template(payload: TemplateCreate, db: Session ,current_user: CurrentUser,):
 
        # user = db.query(User).filter(User.user_id == payload.user_id).first()
        # if not user:
        #     raise HTTPException(404, "User not found")

        data = payload.dict()

        data.pop("user_id",None)
        data["created_by"] = current_user.username
        tasks = data.pop("tasks", None)

        template = Template(**data)
        db.add(template)
        db.flush()  
        max_sort = (
            db.query(func.max(Template.sort_order))
            .filter(Template.is_active == True)
            .scalar()
        )
        template.sort_order = (max_sort or 0) + 1
        db.commit()
        db.refresh(template)

        if tasks:
            for task_payload in tasks:
                # task_user = db.query(User).filter(User.user_id == task_payload.user_id).first() if hasattr(task_payload, 'user_id') else user
                task_data = task_payload.dict() if hasattr(task_payload, 'dict') else task_payload
                task_data.pop("user_id", None)
                task_data["template_id"] = template.template_id
                task_data["priority_id"] = TASK_PRIORITY_HIGH
                task_data["status_id"] = TASK_STATUS
                task_data["created_by"] = current_user.username
                task_data["dependency_type"] = DEPENDENCY_TYPE
                
                depends_on = task_data.pop("depends_on", None)

                if depends_on:
                    task_data["dependent_taskid"] = depends_on

                    dep_task = db.query(TemplateTaskMapping).filter(
                        TemplateTaskMapping.template_task_mapping_id == depends_on
                    ).first()

                    if dep_task and dep_task.start_date and task_data.get("start_date"):
                        child = task_data["start_date"]
                        parent = dep_task.start_date

                        if hasattr(child, "date"):
                            child = child.date()
                        if hasattr(parent, "date"):
                            parent = parent.date()

                        task_data["days_offset"] = (child - parent).days
                    else:
                        task_data["days_offset"] = 0

                else:
                    task_data["dependent_taskid"] = None
                    task_data["days_offset"] = 0


                if task_data.get("parent_id"):
                    task_data["dependent_taskid"] = task_data["parent_id"]

                    parent = db.query(TemplateTaskMapping).filter(
                        TemplateTaskMapping.template_task_mapping_id == task_data["parent_id"]
                    ).first()
                    if parent and parent.start_date and task_data["start_date"]:

                        child_date = task_data["start_date"]
                        parent_date = parent.start_date

                        if hasattr(child_date, "date"):
                            child_date = child_date.date()

                        if hasattr(parent_date, "date"):
                            parent_date = parent_date.date()

                        task_data["days_offset"] = (child_date - parent_date).days
                    else:
                        task_data["days_offset"] = 0

                if task_data.get("parent_id"):
                    max_sort = (
                        db.query(func.max(TemplateTaskMapping.sort_order))
                        .filter(
                            TemplateTaskMapping.template_id == template.template_id,
                            TemplateTaskMapping.parent_id == task_data["parent_id"],
                            TemplateTaskMapping.is_active == True,
                        )
                        .scalar()
                    )
                else:
                    max_sort = (
                        db.query(func.max(TemplateTaskMapping.sort_order))
                        .filter(
                            TemplateTaskMapping.template_id == template.template_id,
                            TemplateTaskMapping.parent_id == None,
                            TemplateTaskMapping.is_active == True,
                        )
                        .scalar()
                    )

                task_data["sort_order"] = (max_sort or 0) + 1


                task = TemplateTaskMapping(**task_data)
                db.add(task)
                db.flush()  
            db.commit()

        template = (
            db.query(Template)
            .options(
                joinedload(Template.tasks)
                .joinedload(TemplateTaskMapping.subtasks)
            )
            .filter(Template.template_id == template.template_id, Template.is_active == True)
            .first()
        )
        if template:
            template.tasks = [task for task in template.tasks if task.parent_id is None]
        await manager.broadcast({
            "type": "template_create",
            "template_id": template.template_id,
            "template_name": template.template_name,
            "created_by": current_user.username
        })
        print("🔥 Broadcasted template_create event")

        return template

    
    @staticmethod
    async def copy_template(payload: TemplateCopyOptions, db: Session , current_user: CurrentUser,):
        if bool(payload.source_template_id) == bool(payload.source_task_id):
            raise HTTPException(400, "Provide either source_template_id or source_task_id")

        # ───────── BRANCH 1: COPY WHOLE TEMPLATE ─────────
        if payload.source_template_id:
            src = (
                db.query(Template)
                .options(
                    joinedload(Template.tasks)
                    .joinedload(TemplateTaskMapping.subtasks)
                )
                .filter(Template.template_id == payload.source_template_id,
                        Template.is_active == True)
                .first()
            )
            if not src:
                raise HTTPException(404, "Source template not found")

            user = current_user

            # 1) create new template
            new_tpl = Template(
                template_name=f"{src.template_name} - Copy",
                template_description=src.template_description if payload.copy_tasks else None,
                created_by=current_user.username,
                is_active=True,
            )
            db.add(new_tpl)
            db.flush()
            max_tpl_sort = (
                db.query(func.max(Template.sort_order))
                .filter(Template.is_active == True)
                .scalar()
            )
            new_tpl.sort_order = (max_tpl_sort or 0) + 1

            # 2) optionally copy tasks + subtasks
            if payload.copy_tasks:
                id_map: dict[int, int] = {}

                # Only consider active tasks from source template
                src.tasks = [t for t in (src.tasks or []) if getattr(t, 'is_active', False)]
                for t in src.tasks:
                    t.subtasks = [st for st in (t.subtasks or []) if getattr(st, 'is_active', False)]

                # parent tasks
                # ensure we do not copy deleted/inactive tasks
                active_tasks = [t for t in src.tasks if t.is_active]
                for t in active_tasks:
                    t.subtasks = [st for st in t.subtasks if st.is_active]
                parent_tasks = [t for t in active_tasks if t.parent_id is None]
                for t in parent_tasks:
                    nt = TemplateTaskMapping(
                        template_id=new_tpl.template_id,
                        task_name=t.task_name,
                        priority_id=t.priority_id,
                        isMilestone=t.isMilestone,
                        dependency_type=t.dependency_type,
                        days_offset=t.days_offset,
                        parent_id=None,
                        dependent_taskid=None,
                        status_id=t.status_id,
                        # sort_order=t.sort_order,
                        created_by=current_user.username,
                        is_active=True,
                    )
                    db.add(nt)
                    db.flush()
                    id_map[t.template_task_mapping_id] = nt.template_task_mapping_id

                if payload.copy_subtasks:
                    for t in active_tasks:
                        if t.parent_id is None:
                            continue
                        if t.parent_id not in id_map:
                            continue
                        # only copy active subtasks (we already filtered above)
                        nt = TemplateTaskMapping(
                            template_id=new_tpl.template_id,
                            task_name=t.task_name,
                            priority_id=t.priority_id,
                            isMilestone=t.isMilestone,
                            dependency_type=t.dependency_type,
                            days_offset=t.days_offset,
                            parent_id=id_map.get(t.parent_id),
                            dependent_taskid=id_map.get(t.dependent_taskid)
                            if t.dependent_taskid in id_map
                            else None,
                            status_id=t.status_id,
                            # subtask_sort_order=st.subtask_sort_order,
                            created_by=current_user.username,
                            is_active=True,
                        )
                        db.add(nt)
                        db.flush()

            db.commit()
            db.refresh(new_tpl)
            payload = {
                "type": "template_copied",
                "new_template_id": new_tpl.template_id,
                "source_template_id": payload.source_template_id,
                "template_name": new_tpl.template_name
            }
            await manager.broadcast(payload)
            print(f"✅ Broadcast TEMPLATE COPY: new_template_id={new_tpl.template_id}")

            tpl = (
                db.query(Template)
                .options(
                    joinedload(Template.tasks.and_(TemplateTaskMapping.parent_id == None))
                    .joinedload(TemplateTaskMapping.subtasks)
                )
                .filter(Template.template_id == new_tpl.template_id,
                        Template.is_active == True)
                .first()
            )
            return TemplateOut.from_orm(tpl)

        # ───────── BRANCH 2: COPY ONE TASK / SUBTASK ─────────
        src = (
            db.query(TemplateTaskMapping)
            .options(joinedload(TemplateTaskMapping.subtasks))
            .filter(TemplateTaskMapping.template_task_mapping_id == payload.source_task_id,
                    TemplateTaskMapping.is_active == True)
            .first()
        )
        if not src:
            raise HTTPException(404, "Task not found")

        template_id = src.template_id

        # 1) copy this task in SAME template and SAME parent
        new_task = TemplateTaskMapping(
            template_id=template_id,
            task_name=f"{src.task_name} - Copy",
            priority_id=src.priority_id,
            isMilestone=src.isMilestone,
            dependency_type=src.dependency_type,
            days_offset=src.days_offset,
            parent_id=src.parent_id,
            dependent_taskid=src.dependent_taskid,
            status_id=src.status_id,
            created_by=current_user.username,
            is_active=True,
        )
        db.add(new_task)
        db.flush()

        id_map: dict[int, int] = {src.template_task_mapping_id: new_task.template_task_mapping_id}

        # 2) copy its direct subtasks
        if payload.copy_subtasks:
            for st in src.subtasks:
                if not st.is_active:
                    continue
                clone = TemplateTaskMapping(
                    template_id=template_id,
                    task_name=st.task_name,
                    priority_id=st.priority_id,
                    isMilestone=st.isMilestone,
                    dependency_type=st.dependency_type,
                    days_offset=st.days_offset,
                    parent_id=new_task.template_task_mapping_id,
                    dependent_taskid=id_map.get(st.dependent_taskid),
                    status_id=st.status_id,
                    created_by=current_user.username,
                    is_active=True,
                )
                db.add(clone)
                db.flush()
                id_map[st.template_task_mapping_id] = clone.template_task_mapping_id

        db.commit()
        db.refresh(new_task)
        payload = {
            "type": "template_task_copied",
            "new_task_id": new_task.template_task_mapping_id,
            "source_task_id": payload.source_task_id,
            "template_id": template_id,
            "task_name": new_task.task_name
        }

        if src.parent_id is not None:
            payload["parent_id"] = new_task.parent_id

        await manager.broadcast(payload)
        print(f"✅ Broadcast TASK COPY: new_task_id={new_task.template_task_mapping_id}")
        task_with_subs = (
            db.query(TemplateTaskMapping)
            .options(joinedload(TemplateTaskMapping.subtasks))
            .filter(TemplateTaskMapping.template_task_mapping_id == new_task.template_task_mapping_id,
                    TemplateTaskMapping.is_active == True)
            .first()
        )
        return TemplateTaskOut.from_orm(task_with_subs)
    
    @staticmethod
    async def list_templates(db: Session , current_user: CurrentUser):
        templates = (
        db.query(Template)
        .options(
            joinedload(
                Template.tasks.and_(
                    TemplateTaskMapping.parent_id == None,
                    TemplateTaskMapping.is_active == True
                )
            )
            .joinedload(
                TemplateTaskMapping.subtasks.and_(
                    TemplateTaskMapping.is_active == True
                )
            )
        )
        .filter(Template.is_active == True)
        .order_by(
            case((Template.sort_order == None, 1), else_=0),
            Template.sort_order,
            Template.template_id,
        )
        .all()
    )
        for tpl in templates:
            parent_tasks = sorted(
                tpl.tasks,
                key=lambda t: (
                    t.sort_order is None,
                    t.sort_order,
                    t.template_task_mapping_id,
                ),
            )
            tpl.tasks = parent_tasks

            for t in tpl.tasks:
                t.subtasks = sorted(
                    t.subtasks,
                    key=lambda s: (
                        s.subtask_sort_order is None,
                        s.subtask_sort_order,
                        s.template_task_mapping_id,
                    ),
                )
            await manager.broadcast({
                "type": "templates_list_refreshed",
                "count": len(templates),
                "refreshed_by": current_user.username
            })
            print("🔥 Broadcasted templates_list_refreshed event")

        return templates
    
    @staticmethod
    def reorder_templates(
        payload: TemplateReorderRequest,
        db: Session ,
        current_user: CurrentUser,
    ):
        positions = payload.items

        if not positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reorder payload",
            )

        template_items = [p for p in positions if hasattr(p, "template_id") and not hasattr(p, "task_id")]
        task_items     = [p for p in positions if hasattr(p, "task_id") and p.parent_task_id is None]
        subtask_items  = [p for p in positions if hasattr(p, "task_id") and p.parent_task_id is not None]

        # ───────────── TEMPLATE REORDER ─────────────
        if template_items:
            tpl_ids = [p.template_id for p in template_items]

            templates = (
                db.query(Template)
                .filter(
                    Template.template_id.in_(tpl_ids),
                    Template.is_active == True,
                )
                .all()
            )
            valid_ids = {t.template_id for t in templates}

            for tid in tpl_ids:
                if tid not in valid_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid template id in reorder payload",
                    )

            templates_by_id = {t.template_id: t for t in templates}
            for item in template_items:
                tpl = templates_by_id[item.template_id]
                tpl.sort_order = item.position

        # ───────────── TEMPLATE TASK REORDER (top-level) ─────────────
        if task_items:
            task_ids = [p.task_id for p in task_items]

            tasks = (
                db.query(TemplateTaskMapping)
                .filter(
                    TemplateTaskMapping.template_task_mapping_id.in_(task_ids),
                    TemplateTaskMapping.is_active == True,
                    TemplateTaskMapping.parent_id == None,
                )
                .all()
            )
            valid_task_ids = {t.template_task_mapping_id for t in tasks}

            for tid in task_ids:
                if tid not in valid_task_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid task id in reorder payload",
                    )

            tasks_by_id = {t.template_task_mapping_id: t for t in tasks}
            for item in task_items:
                task = tasks_by_id[item.task_id]
                task.sort_order = item.position

        # ───────────── SUBTASK REORDER ─────────────
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
                db.query(TemplateTaskMapping)
                .filter(
                    TemplateTaskMapping.template_task_mapping_id.in_(subtask_ids),
                    TemplateTaskMapping.is_active == True,
                    TemplateTaskMapping.parent_id == parent_id,
                )
                .all()
            )
            valid_sub_ids = {t.template_task_mapping_id for t in subtasks}

            for tid in subtask_ids:
                if tid not in valid_sub_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid subtask id in reorder payload",
                    )

            subtasks_by_id = {t.template_task_mapping_id: t for t in subtasks}
            for item in subtask_items:
                st = subtasks_by_id[item.task_id]
                st.subtask_sort_order = item.position

        db.commit()
        return None

    
    @staticmethod
    async def get_template(template_id: int, db: Session,current_user: CurrentUser,):

        template = (
            db.query(Template)
            .options(
                joinedload(Template.tasks.and_(TemplateTaskMapping.parent_id == None))
                .joinedload(TemplateTaskMapping.subtasks)
            )
            .filter(Template.template_id == template_id, Template.is_active == True)
            .first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        template.tasks = [
            t for t in (template.tasks or []) if t.parent_id is None
        ]
        for t in template.tasks:
            t.subtasks = t.subtasks or []
        
        await manager.broadcast({
            "type": "template_viewed", 
            "template_id": template_id,
            "template_name": template.template_name,
            "viewed_by": current_user.username
        })
        print(f"🔥 Broadcasted template_viewed event: template_id={template_id}")
        return template
    
    @staticmethod
    async def update_template(template_id: int, payload: TemplateUpdate, db: Session,current_user: CurrentUser,):
        template = db.get(Template, template_id)
        if not template:
            raise HTTPException(404, "Template not found")

        update_data = payload.dict(exclude_unset=True)

        # user = None
        # if hasattr(payload, 'modified_by_user_id') and payload.modified_by_user_id:
        #     user = db.query(User).filter(User.user_id == payload.modified_by_user_id).first()
        #     if not user:
        #         raise HTTPException(404, "User not found")
        #     update_data["modified_by"] = user.username

        update_data.pop("modified_by", None)
        template.modified_by = current_user.username
        template.modified_at = datetime.utcnow()

        for key, value in update_data.items():
            setattr(template, key, value)

        db.commit()
        db.refresh(template)
        await manager.broadcast({
            "type": "template_update",
            "template_id": template_id,
            "template_name": template.template_name,
            "updated_by": current_user.username
        })
        print("🔥 Broadcasted template_update event")
        return template
    
    # @staticmethod
    # def delete_template(template_id: int, db: Session = Depends(get_db)):
    #     template = db.get(Template, template_id)
    #     if not template:
    #         raise HTTPException(404, "Template not found")
    #     template.is_active = False
    #     db.commit()
    #     return None


    @staticmethod
    async def delete_template(template_id: int, db: Session):
        template = (
            db.query(Template)
            .filter(
                Template.template_id == template_id,
                Template.is_active == True
            )
            .first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        db.query(Template).filter(
            Template.template_id == template_id
        ).update(
            {Template.is_active: False},
            synchronize_session=False,
        )

        db.commit()
        await manager.broadcast({
            "type": "template_delete",
            "template_id": template_id
        })
        print("🔥 Broadcasted template_delete event")
        return {"message": "Template soft deleted successfully"}
