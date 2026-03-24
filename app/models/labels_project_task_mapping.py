# app/models/labels_project_task_mapping.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class LabelsProjectTaskMapping(Base):
    __tablename__ = "labels_project_task_mapping"

    labels_project_task_mapping_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    label_id = Column(Integer, ForeignKey("labels.labels_id"), nullable=False)
    project_id = Column(Integer, ForeignKey("Projects.project_id",ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("Project_task_mapping.project_task_mapping_id",ondelete="CASCADE"), nullable=True)
    project_label_category_id = Column(Integer, ForeignKey("system_constants.id"), nullable=True)

    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    modified_by = Column(String(255), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, nullable=True)

    # relationships
    label = relationship("Label", backref="label_mappings")
    project = relationship("Project", backref="label_project_mappings")
    task = relationship("ProjectTaskMapping", backref="label_task_mappings")
    project_label_category = relationship("SystemConstant", foreign_keys=[project_label_category_id])
