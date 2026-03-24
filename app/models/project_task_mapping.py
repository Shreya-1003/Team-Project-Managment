# app/models/project_task_mapping.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ProjectTaskMapping(Base):
    __tablename__ = "Project_task_mapping"   

    id = Column(
        Integer,
        name="project_task_mapping_id",
        primary_key=True,
        autoincrement=True,
        index=True
    )

    project_id = Column(Integer, ForeignKey("Projects.project_id",ondelete="CASCADE"), nullable=False)

    task_name = Column(String(255), nullable=False)

    priority_id = Column(Integer, ForeignKey("system_constants.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("system_constants.id"), nullable=True)

    is_milestone = Column(Boolean, name="isMilestone", nullable=True)

    dependent_task_id = Column(
        Integer,
        ForeignKey("Project_task_mapping.project_task_mapping_id", ondelete="SET NULL"),
        name="dependent_taskid",
        nullable=True
    )

    parent_id = Column(
        Integer,
        ForeignKey("Project_task_mapping.project_task_mapping_id", ondelete="SET NULL"),
        nullable=True
    )

    dependency_type = Column(String(50), nullable=True)
    days_offset = Column(Integer, nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    
    created_by = Column(String(36), nullable=True)
    modified_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    sort_order = Column(Integer, nullable=True, index=True)           
    subtask_sort_order = Column(Integer, nullable=True, index=True)   


    # Relationships
    project = relationship("Project", back_populates="tasks")

    parent_task = relationship(
        "ProjectTaskMapping",
        remote_side=[id],
        back_populates="subtasks",
        foreign_keys=[parent_id]
    )
    subtasks = relationship(
        "ProjectTaskMapping",
        back_populates="parent_task",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id]
    )

    # Dependency relationships 
    # depends_on = relationship(
    #     "ProjectTaskMapping",
    #     remote_side=[id],
    #     back_populates="dependents",
    #     foreign_keys=[dependent_task_id]
        
    # )
    # dependents = relationship(
    #     "ProjectTaskMapping",
    #     back_populates="depends_on",
    #     foreign_keys=[dependent_task_id]
    # )

    # Assigned users
    users = relationship("UserTaskMapping", back_populates="tasks")


 