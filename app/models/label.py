# app/models/label.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Label(Base):
    __tablename__ = "labels"

    labels_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    label_text = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("system_constants.id"), nullable=False)

    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    modified_by = Column(String(255), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # relationships
    category = relationship("SystemConstant", foreign_keys=[category_id])
    sort_order = Column(Integer, nullable=True)