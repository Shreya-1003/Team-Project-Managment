# app/models/project.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Project(Base):
    __tablename__ = "Projects"         

  
    id = Column(Integer, name="project_id", primary_key=True, autoincrement=True, index=True)
    name = Column(String(255), name="project_name", nullable=False, index=True)
    description = Column(Text, name="project_description", nullable=True)


    status_id = Column(Integer, ForeignKey("system_constants.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("Template.template_id", ondelete="SET NULL"), nullable=True)

    sort_order = Column(Integer, nullable=True, index=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_by = Column(String(36), nullable=True)
    modified_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

   
    template = relationship("Template", back_populates="projects")   

    tasks = relationship(
        "ProjectTaskMapping",
        back_populates="project",
        cascade="all, delete-orphan"
    )