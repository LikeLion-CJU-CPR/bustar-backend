
from pydantic import BaseModel
from typing import Optional

class PurchaseRequest(BaseModel):
    user_id: int
    product_amount: int
    granted_coupon_id: Optional[int] = None
