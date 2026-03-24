# app/models/user_task_mapping.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship

class UserTaskMapping(Base):
    __tablename__ = "user_task_mapping"

    id = Column(Integer, name="user_task_mapping_id", primary_key=True, autoincrement=True, index=True)
    task_id = Column(Integer, ForeignKey("Project_task_mapping.project_task_mapping_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"), nullable=False)

    created_by = Column(String(36), nullable=True)
    modified_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tasks = relationship("ProjectTaskMapping", back_populates="users")
    user = relationship("User", back_populates="tasks")