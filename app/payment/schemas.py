from pydantic import BaseModel
from typing import Optional
from app.payment.models import PaymentStatus, PaymentType


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: PaymentStatus
    payment_type: Optional[PaymentType] = None

    class Config:
        from_attributes = True
