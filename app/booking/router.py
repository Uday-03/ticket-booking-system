from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.auth.utils import get_current_user
from app.auth.models import User
from app.booking.models import (
    SeatAvailability, SeatStatus,
    Booking, BookingStatus,
    BookingSeat, Ticket,
)
from app.booking.schemas import (
    SeatAvailabilityResponse,
    BlockSeatsRequest, BlockSeatsResponse,
    ConfirmBookingResponse,
    TicketResponse, BookingResponse,
)
from app.admin.models import Show, Seat, Screen
from app.movies.models import Movie
from app.payment.models import Payment, PaymentStatus
from app.payment.tasks import process_payment_task

router = APIRouter(prefix="/booking", tags=["Booking"])


@router.get("/shows/{show_id}/seats", response_model=List[SeatAvailabilityResponse])
def get_seat_availability(show_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    availability = db.query(SeatAvailability).filter(SeatAvailability.show_id == show_id).all()

    result = []
    for av in availability:
        seat = db.query(Seat).filter(Seat.id == av.seat_id).first()
        result.append(SeatAvailabilityResponse(
            seat_id=seat.id,
            seat_number=seat.seat_number,
            seat_type=seat.seat_type.value,
            price=seat.price,
            status=av.status,
        ))
    return result


@router.post("/block-seats", response_model=BlockSeatsResponse)
def block_seats(
    payload: BlockSeatsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    show = db.query(Show).filter(Show.id == payload.show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    # Lock rows for atomic seat blocking
    availabilities = (
        db.query(SeatAvailability)
        .filter(
            SeatAvailability.show_id == payload.show_id,
            SeatAvailability.seat_id.in_(payload.seat_ids),
        )
        .with_for_update()  # row-level lock — prevents double booking
        .all()
    )

    if len(availabilities) != len(payload.seat_ids):
        raise HTTPException(status_code=400, detail="One or more seats not found for this show")

    for av in availabilities:
        if av.status != SeatStatus.AVAILABLE:
            raise HTTPException(
                status_code=409,
                detail=f"Seat {av.seat_id} is not available (status: {av.status.value})",
            )

    # Calculate total
    total_amount = 0.0
    for seat_id in payload.seat_ids:
        seat = db.query(Seat).filter(Seat.id == seat_id).first()
        total_amount += seat.price

    # Create pending booking
    booking = Booking(
        user_id=current_user.id,
        show_id=payload.show_id,
        total_amount=total_amount,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.flush()  # get booking.id

    # Add booking seats
    for seat_id in payload.seat_ids:
        db.add(BookingSeat(booking_id=booking.id, seat_id=seat_id))

    # Block the seats
    now = datetime.now(timezone.utc)
    for av in availabilities:
        av.status = SeatStatus.BLOCKED
        av.blocked_by = current_user.id
        av.blocked_at = now

    db.commit()
    db.refresh(booking)

    return BlockSeatsResponse(
        booking_id=booking.id,
        show_id=payload.show_id,
        seat_ids=payload.seat_ids,
        total_amount=total_amount,
        message="Seats blocked for 10 minutes. Proceed to payment.",
    )


@router.post("/confirm/{booking_id}", response_model=ConfirmBookingResponse)
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Booking is already {booking.status.value}")

    # Dispatch async payment task via Celery
    process_payment_task.delay(booking_id)

    return ConfirmBookingResponse(
        booking_id=booking_id,
        status=BookingStatus.PENDING,
        message="Payment is being processed. Check your booking status shortly.",
    )


@router.post("/cancel/{booking_id}", response_model=ConfirmBookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking already cancelled")

    # Release seats
    seat_ids = [bs.seat_id for bs in booking.seats]
    db.query(SeatAvailability).filter(
        SeatAvailability.show_id == booking.show_id,
        SeatAvailability.seat_id.in_(seat_ids),
    ).update(
        {
            SeatAvailability.status: SeatStatus.AVAILABLE,
            SeatAvailability.blocked_by: None,
            SeatAvailability.blocked_at: None,
        },
        synchronize_session=False,
    )

    booking.status = BookingStatus.CANCELLED

    # Refund if payment was successful
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment and payment.status == PaymentStatus.SUCCESS:
        payment.status = PaymentStatus.REFUNDED

    db.commit()

    return ConfirmBookingResponse(
        booking_id=booking_id,
        status=BookingStatus.CANCELLED,
        message="Booking cancelled successfully.",
    )


@router.get("/my-bookings", response_model=List[BookingResponse])
def my_bookings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Booking).filter(Booking.user_id == current_user.id).all()


@router.get("/ticket/{booking_id}", response_model=TicketResponse)
def get_ticket(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Ticket only available for confirmed bookings")

    ticket = db.query(Ticket).filter(Ticket.booking_id == booking_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket
