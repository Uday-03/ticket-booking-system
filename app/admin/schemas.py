from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time
from app.admin.models import SeatType


# Theatre
class TheatreCreate(BaseModel):
    name: str
    location: str

class TheatreResponse(BaseModel):
    id: int
    name: str
    location: str

    class Config:
        from_attributes = True


# Screen
class ScreenCreate(BaseModel):
    name: str
    theatre_id: int

class ScreenAssignMovie(BaseModel):
    movie_id: int

class ScreenResponse(BaseModel):
    id: int
    name: str
    theatre_id: int
    current_movie_id: Optional[int] = None

    class Config:
        from_attributes = True


# Seat
class SeatCreate(BaseModel):
    seat_number: str
    seat_type: SeatType
    price: float

class SeatBulkCreate(BaseModel):
    seats: List[SeatCreate]

class SeatResponse(BaseModel):
    id: int
    screen_id: int
    seat_number: str
    seat_type: SeatType
    price: float

    class Config:
        from_attributes = True


# Show
class ShowCreate(BaseModel):
    screen_id: int
    movie_id: int
    show_date: date
    start_time: time
    end_time: time

class ShowResponse(BaseModel):
    id: int
    screen_id: int
    movie_id: int
    show_date: date
    start_time: time
    end_time: time

    class Config:
        from_attributes = True


# Movie (admin creates/manages movies)
class MovieCreate(BaseModel):
    name: str
    language: str
    duration_minutes: int
    rating: float = 0.0
    description: Optional[str] = None
