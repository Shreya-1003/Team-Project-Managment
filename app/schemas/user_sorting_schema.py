from pydantic import BaseModel
from typing import List

class UserProjectReorderItem(BaseModel):
    project_id: int     
    position: int        

class UserProjectReorderRequest(BaseModel):
    user_id: int
    items: List[UserProjectReorderItem]

