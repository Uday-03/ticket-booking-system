from datetime import datetime, timezone, timedelta
from app.payment.celery_app import celery_app
from app.database import SessionLocal
from app.booking.models import SeatAvailability, SeatStatus, Booking, BookingStatus
from app.config import settings


@celery_app.task(name="app.booking.tasks.release_expired_seats")
def release_expired_seats():
    """
    Periodic task: runs every minute.
    Releases seats that have been BLOCKED beyond the timeout window (10 mins).
    Also cancels the associated pending booking.
    """
    db = SessionLocal()
    try:
        expiry_threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.SEAT_BLOCK_TIMEOUT)

        expired = db.query(SeatAvailability).filter(
            SeatAvailability.status == SeatStatus.BLOCKED,
            SeatAvailability.blocked_at <= expiry_threshold,
        ).all()

        if not expired:
            return

        expired_show_seat_pairs = [(av.show_id, av.seat_id) for av in expired]

        for av in expired:
            av.status = SeatStatus.AVAILABLE
            av.blocked_by = None
            av.blocked_at = None

        # Cancel any PENDING bookings associated with these expired seats
        for av in expired:
            bookings = db.query(Booking).filter(
                Booking.show_id == av.show_id,
                Booking.status == BookingStatus.PENDING,
            ).all()
            for booking in bookings:
                booking.status = BookingStatus.CANCELLED

        db.commit()
        print(f"[Seat Expiry] Released {len(expired)} expired blocked seats.")

    except Exception as e:
        db.rollback()
        print(f"[Seat Expiry] Error: {e}")
    finally:
        db.close()
