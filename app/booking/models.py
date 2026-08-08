import enum
from sqlalchemy import Column, Integer, Float, ForeignKey, Enum, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SeatStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    BOOKED = "BOOKED"


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class SeatAvailability(Base):
    __tablename__ = "seat_availability"

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False)
    blocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # user who blocked it
    blocked_at = Column(DateTime(timezone=True), nullable=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    seats = relationship("BookingSeat", back_populates="booking")
    ticket = relationship("Ticket", back_populates="booking", uselist=False)
    payment = relationship("Payment", back_populates="booking", uselist=False)


class BookingSeat(Base):
    __tablename__ = "booking_seats"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)

    booking = relationship("Booking", back_populates="seats")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    movie_name = Column(String(200), nullable=False)
    screen_name = Column(String(100), nullable=False)
    show_date = Column(String(20), nullable=False)
    show_time = Column(String(20), nullable=False)
    seat_details = Column(String(500), nullable=False)  # e.g. "A1(GOLD), A2(GOLD)"
    total_amount = Column(Float, nullable=False)

    booking = relationship("Booking", back_populates="ticket")
