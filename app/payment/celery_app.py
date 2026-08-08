from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "ticket_booking",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.payment.tasks", "app.booking.tasks"],
)

celery_app.conf.beat_schedule = {
    # Run every minute to release expired blocked seats
    "release-expired-blocked-seats": {
        "task": "app.booking.tasks.release_expired_seats",
        "schedule": 60.0,  # every 60 seconds
    },
}
