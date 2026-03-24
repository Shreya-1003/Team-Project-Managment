from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship

class Template(Base):
    __tablename__ = "Template"
    template_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    template_name = Column(String(255), nullable=True)
    template_description = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)


    sort_order = Column(Integer, nullable=True, index=True)

    # Relationships
    tasks = relationship("TemplateTaskMapping", back_populates="template", cascade="all, delete-orphan", lazy="joined")
    projects = relationship("Project", back_populates="template")