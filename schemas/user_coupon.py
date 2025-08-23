
from pydantic import BaseModel
from typing import Optional

class UserCouponCreate(BaseModel):
    id: int
    coupon_id: int
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    use_can: int
    use_finish: int
    finish_period: int


class UserCouponUpdate(BaseModel):
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    use_can: Optional[int] = None
    use_finish: Optional[int] = None
    finish_period: Optional[int] = None
