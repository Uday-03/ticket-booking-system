from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.utils import get_current_user
from app.auth.models import User
from app.payment.models import Payment
from app.payment.schemas import PaymentResponse

router = APIRouter(prefix="/payment", tags=["Payment"])


@router.get("/{booking_id}", response_model=PaymentResponse)
def get_payment_status(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for this booking")
    return payment
