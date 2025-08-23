
from pydantic import BaseModel
from typing import Optional

class CouponCreate(BaseModel):
    coupon_name: str
    coupon_price: int
    coupon_discount: Optional[int] = None
    coupon_affiliate: Optional[str] = None
    coupon_period: Optional[str] = None


class CouponUpdate(BaseModel):
    coupon_name: Optional[str] = None
    coupon_price: Optional[int] = None
    coupon_discount: Optional[int] = None
    coupon_affiliate: Optional[str] = None
    coupon_period: Optional[str] = None
