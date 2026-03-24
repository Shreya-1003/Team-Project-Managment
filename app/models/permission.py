# app/models/permission.py
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship

class Permission(Base):
    __tablename__ = "Permissions"

    id = Column(Integer, name="permission_id", primary_key=True, autoincrement=True, index=True)
    permission_type = Column(String(100), nullable=False)
    permission_bracket = Column(String(100), nullable=True)
    created_by = Column(String(36), nullable=True)
    modified_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship to users via mapping
    users = relationship("UserPermissionMapping", back_populates="permission")