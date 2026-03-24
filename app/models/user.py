# app/models/user.py
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "Users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    username = Column(String(255), nullable=False)
    status_id = Column(Integer, ForeignKey("system_constants.id"), nullable=True)

    # Audit
    created_by = Column(String(36), nullable=True)
    modified_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    profile_picture = Column(String(500), nullable=True)

    # Relationships
    permissions = relationship("UserPermissionMapping", back_populates="user")
    tasks = relationship("UserTaskMapping", back_populates="user")

   