from app.payment.celery_app import celery_app
from app.database import SessionLocal
from app.auth.models import User  # noqa: F401 — required for FK resolution
from app.movies.models import Movie
from app.admin.models import Show, Screen, Seat, Theatre  # noqa: F401
from app.booking.models import Booking, BookingStatus, BookingSeat, Ticket, SeatAvailability, SeatStatus
from app.payment.models import Payment, PaymentStatus


@celery_app.task(name="app.payment.tasks.process_payment_task", bind=True, max_retries=3)
def process_payment_task(self, booking_id: int):
    """
    Simulates async payment processing.
    In production, this would integrate with a real payment gateway.
    On success: confirms booking, marks seats as BOOKED, creates ticket.
    On failure: cancels booking, releases seats.
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking or booking.status != BookingStatus.PENDING:
            return

        # Create payment record
        payment = Payment(
            booking_id=booking_id,
            amount=booking.total_amount,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        db.flush()

        # --- Simulate payment gateway call ---
        # In production: call Stripe/Razorpay/etc. here
        payment_success = True  # Simulated success

        if payment_success:
            payment.status = PaymentStatus.SUCCESS

            # Confirm booking
            booking.status = BookingStatus.CONFIRMED

            # Mark seats as BOOKED
            seat_ids = [bs.seat_id for bs in booking.seats]
            db.query(SeatAvailability).filter(
                SeatAvailability.show_id == booking.show_id,
                SeatAvailability.seat_id.in_(seat_ids),
            ).update(
                {SeatAvailability.status: SeatStatus.BOOKED},
                synchronize_session=False,
            )

            # Build ticket
            show = db.query(Show).filter(Show.id == booking.show_id).first()
            screen = db.query(Screen).filter(Screen.id == show.screen_id).first()
            movie = db.query(Movie).filter(Movie.id == show.movie_id).first()

            seat_details_parts = []
            for seat_id in seat_ids:
                seat = db.query(Seat).filter(Seat.id == seat_id).first()
                seat_details_parts.append(f"{seat.seat_number}({seat.seat_type.value})")

            ticket = Ticket(
                booking_id=booking_id,
                movie_name=movie.name,
                screen_name=screen.name,
                show_date=str(show.show_date),
                show_time=str(show.start_time),
                seat_details=", ".join(seat_details_parts),
                total_amount=booking.total_amount,
            )
            db.add(ticket)

        else:
            # Payment failed — release seats and cancel booking
            payment.status = PaymentStatus.FAILED
            booking.status = BookingStatus.CANCELLED

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

        db.commit()

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()
