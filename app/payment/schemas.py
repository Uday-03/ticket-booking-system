from pydantic import BaseModel
from app.payment.models import PaymentStatus, PaymentType


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: PaymentStatus
    payment_type: PaymentType = None

    class Config:
        from_attributes = True
