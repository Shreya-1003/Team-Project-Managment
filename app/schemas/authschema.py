from pydantic import BaseModel
from typing import Optional

class CurrentUser(BaseModel):
    user_id: int
    username: str       
    email: Optional[str] = None
