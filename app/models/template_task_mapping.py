from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class TemplateTaskMapping(Base):
    __tablename__ = "Template_task_mapping"
    template_task_mapping_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    template_id = Column(Integer, ForeignKey("Template.template_id", ondelete="CASCADE"), nullable=True, index=True)
    task_name = Column(String(255), nullable=True)
    priority_id = Column(Integer, ForeignKey("system_constants.id"), nullable=True, index=True)
    isMilestone = Column(Boolean, nullable=True)
    dependent_taskid = Column(Integer, ForeignKey("Template_task_mapping.template_task_mapping_id", ondelete="SET NULL"), nullable=True)
    dependency_type = Column(Integer, ForeignKey("system_constants.id"), nullable=True, index=True)
    days_offset = Column(Integer, nullable=True)
    parent_id = Column(Integer, ForeignKey("Template_task_mapping.template_task_mapping_id", ondelete="SET NULL"), nullable=True)
    status_id = Column(Integer, ForeignKey("system_constants.id"), nullable=True, index=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)
    modified_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    sort_order = Column(Integer, nullable=True, index=True)           
    subtask_sort_order = Column(Integer, nullable=True, index=True)

    # Relationships
    template = relationship("Template", back_populates="tasks")
    priority = relationship("SystemConstant", foreign_keys=[priority_id])
    status = relationship("SystemConstant", foreign_keys=[status_id])
    dependency = relationship("SystemConstant", foreign_keys=[dependency_type])
    
    parent_task = relationship(
    "TemplateTaskMapping",
    back_populates="subtasks",
    remote_side=[template_task_mapping_id],
    foreign_keys=[parent_id]
)    
    subtasks = relationship(
    "TemplateTaskMapping",
    back_populates="parent_task",
    cascade="all, delete-orphan",
    foreign_keys=[parent_id]
)
#     depends_on = relationship(
#     "TemplateTaskMapping",
#     back_populates="dependents",
#     remote_side=[template_task_mapping_id],
#     foreign_keys=[dependent_taskid]
# )

#     dependents = relationship(
#     "TemplateTaskMapping",
#     back_populates="depends_on",
#     foreign_keys=[dependent_taskid]
# )

