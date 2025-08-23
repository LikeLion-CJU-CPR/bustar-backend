
from pydantic import BaseModel
from typing import Optional

class UsageRecordCreate(BaseModel):
    id: int
    total_use: int
    month_use: int
    saved: int


class UsageRecordUpdate(BaseModel):
    total_use: Optional[int] = None
    month_use: Optional[int] = None
    saved: Optional[int] = None
