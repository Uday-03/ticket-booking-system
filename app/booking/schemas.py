from pydantic import BaseModel
from typing import List
from app.booking.models import BookingStatus, SeatStatus


class SeatAvailabilityResponse(BaseModel):
    seat_id: int
    seat_number: str
    seat_type: str
    price: float
    status: SeatStatus

    class Config:
        from_attributes = True


class BlockSeatsRequest(BaseModel):
    show_id: int
    seat_ids: List[int]


class BlockSeatsResponse(BaseModel):
    booking_id: int
    show_id: int
    seat_ids: List[int]
    total_amount: float
    message: str


class ConfirmBookingResponse(BaseModel):
    booking_id: int
    status: BookingStatus
    message: str


class TicketResponse(BaseModel):
    id: int
    booking_id: int
    movie_name: str
    screen_name: str
    show_date: str
    show_time: str
    seat_details: str
    total_amount: float

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    id: int
    show_id: int
    total_amount: float
    status: BookingStatus
    ticket: TicketResponse = None

    class Config:
        from_attributes = True
