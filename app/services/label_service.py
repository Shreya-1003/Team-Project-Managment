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
from app.schemas.authschema import CurrentUser

from datetime import datetime

class LabelService:
    @staticmethod
    def create_label(payload: LabelCreate, db: Session ,current_user: CurrentUser):
        label_category_type = db.query(SystemConstant).filter(
            SystemConstant.id == LABEL_CATEGORY,
            SystemConstant.is_active == True,
        ).first()
        if not label_category_type:
            raise HTTPException(
                status_code=404,
                detail="Label category type not found in system_constants",
            )

        expected_type = label_category_type.type

        if payload.category_id is None:
            default_cat = db.query(SystemConstant).filter(
                SystemConstant.id == LABEL_CATEGORY_DEFAULT,
                SystemConstant.type == expected_type,
                SystemConstant.is_active == True,
            ).first()
            if not default_cat:
                raise HTTPException(
                    status_code=404,
                    detail="No active label categories found in system_constants",
                )
            payload.category_id = default_cat.id
        else:
            cat = db.query(SystemConstant).filter(
                SystemConstant.id == payload.category_id,
                SystemConstant.type == expected_type,
                SystemConstant.is_active == True,
            ).first()
            if not cat:
                raise HTTPException(
                    status_code=404,
                    detail="Invalid label category passed",
                )
        # user = None
        # if payload.created_by_user_id:
        #     user = db.query(User).filter(User.user_id == payload.created_by_user_id).first()
        #     if not user:
        #         raise HTTPException(status_code=404, detail="User not found")

        data = payload.dict()
        data.pop("created_by", None)

        data["created_by"] = current_user.username

        max_sort = (
            db.query(Label.sort_order)
            .filter(Label.is_active == True, Label.sort_order != None)
            .order_by(Label.sort_order.desc())
            .first()
        )
        next_sort = (max_sort[0] if max_sort else 0) + 1
        data["sort_order"] = next_sort

        label = Label(**data)
        db.add(label)
        db.commit()
        db.refresh(label)
        return label

    
    @staticmethod
    def list_labels(db: Session ,current_user: CurrentUser):
        labels = (
            db.query(Label)
            .filter(Label.is_active == True,)
            .order_by(Label.sort_order, Label.labels_id)
            .all()
        )
        return labels

    
    @staticmethod
    def get_label(label_id: int, db: Session ,current_user: CurrentUser):
        label = db.query(Label).filter(Label.labels_id == label_id, Label.is_active == True,Label.created_by == current_user.username,).first()
        if not label:
            raise HTTPException(status_code=404, detail="Label not found")
        return label
    
    @staticmethod
    def update_label(label_id: int, payload: LabelUpdate, db: Session ,current_user: CurrentUser):
        label = db.query(Label).filter(Label.labels_id == label_id).first()
        if not label or not label.is_active:
            raise HTTPException(status_code=404, detail="Label not found")

        update_data = payload.dict(exclude_unset=True)
        # if "modified_by_user_id" in update_data and update_data["modified_by_user_id"]:
        #     user = db.query(User).filter(User.user_id == update_data["modified_by_user_id"]).first()
        #     if not user:
        #         raise HTTPException(status_code=404, detail="User not found")
        #     update_data["modified_by"] = user.username
        #     update_data.pop("modified_by_user_id", None)

        update_data.pop("modified_by", None)
        label.modified_by = current_user.username

        if "category_id" in update_data:
            label_category_record = db.query(SystemConstant).filter(
                SystemConstant.id == LABEL_CATEGORY,
                SystemConstant.is_active == True
            ).first()
            if not label_category_record:
                raise HTTPException(status_code=404, detail="Label category type not found")
            expected_type = label_category_record.type

            if update_data["category_id"] is None:
                default_cat = db.query(SystemConstant).filter(
                    SystemConstant.type == expected_type,
                    SystemConstant.is_active == True
                ).order_by(SystemConstant.id).first()
                if not default_cat:
                    raise HTTPException(status_code=404, detail="No active label category available")
                update_data["category_id"] = default_cat.id
            else:
                cat = db.query(SystemConstant).filter(
                    SystemConstant.id == update_data["category_id"],
                    SystemConstant.type == expected_type,
                    SystemConstant.is_active == True
                ).first()
                if not cat:
                    raise HTTPException(status_code=404, detail="Label category not found")

        for k, v in update_data.items():
            setattr(label, k, v)

        db.commit()
        db.refresh(label)
        return label
    
    @staticmethod
    def delete_label(label_id: int, db: Session):
        label = (
            db.query(Label)
            .filter(
                Label.labels_id == label_id,
                Label.is_active == True
            )
            .first()
        )

        if not label:
            raise HTTPException(status_code=404, detail="Label not found")

        db.query(Label).filter(
            Label.labels_id == label_id
        ).update(
            {Label.is_active: False},
            synchronize_session=False
        )

        db.commit()
        return {"message": "Label soft deleted successfully"}
