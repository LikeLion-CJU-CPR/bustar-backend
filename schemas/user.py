
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    name: str
    date: str
    grade: Optional[str] = "브론즈"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    grade: Optional[str] = None
