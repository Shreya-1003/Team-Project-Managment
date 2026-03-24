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
from app.schemas.authschema import CurrentUser


class ProjectTaskMappingService:
    @staticmethod
    def create_label_mapping(payload: LabelMappingCreate, db: Session ,current_user: CurrentUser):
        label = db.query(Label).filter(Label.labels_id == payload.label_id, Label.is_active == True).first()
        if not label:
            raise HTTPException(status_code=404, detail="Label not found")

        if payload.project_id:
            proj = db.query(Project).filter(Project.id == payload.project_id, Project.is_active == True).first()
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")

            if payload.task_id:
                task = db.query(ProjectTaskMapping).filter(
                    ProjectTaskMapping.id == payload.task_id,
                    ProjectTaskMapping.is_active == True
                ).first()
                if not task:
                    raise HTTPException(status_code=404, detail="Task not found")

        if payload.project_label_category_id is None:
            project_label_category_record = db.query(SystemConstant).filter(
                SystemConstant.id == PROJECT_LABEL_CATEGORY,
                SystemConstant.is_active == True
            ).first()
            if not project_label_category_record:
                raise HTTPException(status_code=404, detail="Project label category type not found in system_constants")

            expected_type = project_label_category_record.type
            default_cat = db.query(SystemConstant).filter(
                SystemConstant.type == expected_type,
                SystemConstant.is_active == True
            ).order_by(SystemConstant.id).first()
            if not default_cat:
                raise HTTPException(status_code=404, detail="No active project label categories found in system_constants")
            payload.project_label_category_id = default_cat.id  

        expected_type = db.query(SystemConstant).filter(
            SystemConstant.id == PROJECT_LABEL_CATEGORY,
            SystemConstant.is_active == True
        ).first().type

        cat = db.query(SystemConstant).filter(
                SystemConstant.id == payload.project_label_category_id,
                SystemConstant.type == expected_type,
                SystemConstant.is_active == True
        ).first()
        if not cat:
            raise HTTPException(status_code=404, detail="Label category (project_label_category) not found")

        # user = None
        # if payload.created_by_user_id:
        #     user = db.query(User).filter(User.user_id == payload.created_by_user_id).first()
        #     if not user:
        #         raise HTTPException(status_code=404, detail="User not found")


        data = payload.dict()
        data["created_by"] = current_user.username
        data["is_active"] = True
        if data.get("task_id"):
            max_sort = (
                db.query(LabelsProjectTaskMapping.sort_order)
                .filter(
                    LabelsProjectTaskMapping.task_id == data["task_id"],
                    LabelsProjectTaskMapping.is_active == True,
                    LabelsProjectTaskMapping.sort_order != None,
                )
                .order_by(LabelsProjectTaskMapping.sort_order.desc())
                .first()
            )
            next_sort = (max_sort[0] if max_sort else 0) + 1
            data["sort_order"] = next_sort

        mapping = LabelsProjectTaskMapping(**data)
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping
        
    @staticmethod
    def list_mappings(db: Session ,current_user: CurrentUser):
        mappings = db.query(LabelsProjectTaskMapping).filter(LabelsProjectTaskMapping.is_active == True,LabelsProjectTaskMapping.created_by == current_user.username,).all()
        return mappings
    
    @staticmethod
    def get_mapping(mapping_id: int, db: Session ,current_user: CurrentUser):
        mapping = db.query(LabelsProjectTaskMapping).filter(
            LabelsProjectTaskMapping.labels_project_task_mapping_id == mapping_id,
            LabelsProjectTaskMapping.is_active == True,
            LabelsProjectTaskMapping.created_by == current_user.username,
        ).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return mapping
    
    @staticmethod
    def update_label_mapping(mapping_id: int, payload: LabelMappingCreate, db: Session ,current_user: CurrentUser):

        mapping = db.query(LabelsProjectTaskMapping).filter(
            LabelsProjectTaskMapping.labels_project_task_mapping_id == mapping_id,
            LabelsProjectTaskMapping.is_active == True
        ).first()

        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        update_data = payload.dict(exclude_unset=True)

        if payload.label_id:
            label = db.query(Label).filter(
                Label.labels_id == payload.label_id,
                Label.is_active == True
            ).first()
            if not label:
                raise HTTPException(status_code=404, detail="Label not found")

        if payload.project_id:
            proj = db.query(Project).filter(
                Project.id == payload.project_id,
                Project.is_active == True
            ).first()
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")

        if payload.task_id:
            task = db.query(ProjectTaskMapping).filter(
                ProjectTaskMapping.id == payload.task_id,
                ProjectTaskMapping.is_active == True
            ).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

        if "project_label_category_id" in update_data and payload.project_label_category_id is not None:
            expected_type = db.query(SystemConstant).filter(
                SystemConstant.id == PROJECT_LABEL_CATEGORY,
                SystemConstant.is_active == True
            ).first().type

            cat = db.query(SystemConstant).filter(
                SystemConstant.id == payload.project_label_category_id,
                SystemConstant.type == expected_type,
                SystemConstant.is_active == True
            ).first()

            if not cat:
                raise HTTPException(status_code=404, detail="Invalid project label category")

        if payload.project_label_category_id is None:
            project_label_category_record = db.query(SystemConstant).filter(
                SystemConstant.id == PROJECT_LABEL_CATEGORY,
                SystemConstant.is_active == True
            ).first()

            if project_label_category_record:
                expected_type = project_label_category_record.type
                default_cat = db.query(SystemConstant).filter(
                    SystemConstant.type == expected_type,
                    SystemConstant.is_active == True
                ).order_by(SystemConstant.id).first()

                if default_cat:
                    update_data["project_label_category_id"] = default_cat.id

        # user = None
        # if payload.created_by_user_id:
        #     user = db.query(User).filter(User.user_id == payload.created_by_user_id).first()
        #     if not user:
        #         raise HTTPException(status_code=404, detail="User not found")

        update_data["modified_by"] = current_user.username
        update_data["modified_at"] = datetime.utcnow()

        for k, v in update_data.items():
            setattr(mapping, k, v)

        db.commit()
        db.refresh(mapping)
        return mapping
    
    @staticmethod
    def reorder_project_labels(
        payload: ProjectLabelReorderRequest,
        db: Session ,current_user: CurrentUser
    ):
        items = payload.items
        if not items:
            raise HTTPException(status_code=400, detail="Invalid reorder payload")

        label_ids = [i.label_id for i in items]

        labels = (
            db.query(Label)
            .filter(Label.labels_id.in_(label_ids), Label.is_active == True)
            .all()
        )
        found_ids = {l.labels_id for l in labels}
        for lid in label_ids:
            if lid not in found_ids:
                raise HTTPException(status_code=400, detail="Invalid label id in reorder")

        labels_by_id = {l.labels_id: l for l in labels}
        for item in items:
            labels_by_id[item.label_id].sort_order = item.position

        db.commit()
        return None
    
    @staticmethod
    def reorder_task_labels(
        payload: TaskLabelReorderRequest,
        db: Session ,current_user: CurrentUser,
    ):
        items = payload.items
        if not items:
            raise HTTPException(status_code=400, detail="Invalid reorder payload")

        label_ids = [i.mapping_id for i in items]

        labels = (
            db.query(Label)
            .filter(Label.labels_id.in_(label_ids), Label.is_active == True)
            .all()
        )
        if not labels:
            raise HTTPException(
                status_code=400,
                detail="No labels found for reorder",
            )

        found_ids = {l.labels_id for l in labels}
        for lid in label_ids:
            if lid not in found_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid label id (mapping_id) in task-label reorder",
                )

        labels_by_id = {l.labels_id: l for l in labels}
        for item in items:
            labels_by_id[item.mapping_id].sort_order = item.position

        db.commit()
        return None


    @staticmethod
    def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
        mapping = db.query(LabelsProjectTaskMapping).filter(
            LabelsProjectTaskMapping.labels_project_task_mapping_id == mapping_id
        ).first()

        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        db.delete(mapping)
        db.commit()
        return {"message": "Mapping deleted permanently"}