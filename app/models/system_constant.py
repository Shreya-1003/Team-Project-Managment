# app/models/system_constant.py
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.sql import func
from app.database import Base

class SystemConstant(Base):
    __tablename__ = "system_constants"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    type = Column(String(50), nullable=False)  
    name = Column(String(100), nullable=False)  
    status = Column(String(50), nullable=True)  
    created_by = Column(String(36), nullable=True)
    modified_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)