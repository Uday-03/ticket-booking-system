from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.movies.router import router as movies_router
from app.admin.router import router as admin_router
from app.booking.router import router as booking_router
from app.payment.router import router as payment_router

app = FastAPI(
    title="Ticket Booking System",
    description="Movie ticket booking API — resume project",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(movies_router)
app.include_router(admin_router)
app.include_router(booking_router)
app.include_router(payment_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Ticket Booking System is running"}
