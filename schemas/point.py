
from pydantic import BaseModel
from typing import Optional

class PointCreate(BaseModel):
    id: int
    point: int
    use_point: Optional[int] = None
    plus_point: Optional[int] = None
    total_point: int = 0


class PointUpdate(BaseModel):
    point: Optional[int] = None
    use_point: Optional[int] = None
    plus_point: Optional[int] = None
    total_point: Optional[int] = None
