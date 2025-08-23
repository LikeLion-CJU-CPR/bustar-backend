
from pydantic import BaseModel
from typing import Optional

class RecentMoveCreate(BaseModel):
    member_id: int
    origin: str
    destination: str


class RecentMoveUpdate(BaseModel):
    member_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
