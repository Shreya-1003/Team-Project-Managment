from sqlalchemy import Boolean, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class UserSortingMapping(Base):
    __tablename__ = "user_sorting_mapping"

    user_sorting_mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=False)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    sort_order = Column(Integer, nullable=True)

    user = relationship("User", backref="sorting_mappings")
    project = relationship("Project", backref="user_sorting_mappings")

    is_active = Column(Boolean, default=True)
