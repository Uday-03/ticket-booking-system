from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth.utils import require_admin
from app.auth.models import User
from app.admin.models import Theatre, Screen, Seat, Show
from app.admin.schemas import (
    TheatreCreate, TheatreResponse,
    ScreenCreate, ScreenAssignMovie, ScreenResponse,
    SeatBulkCreate, SeatResponse,
    ShowCreate, ShowResponse,
    MovieCreate,
)
from app.movies.models import Movie
from app.movies.schemas import MovieResponse
from app.booking.models import SeatAvailability, SeatStatus

router = APIRouter(prefix="/admin", tags=["Admin"])


# --- Movies ---

@router.post("/movies", response_model=MovieResponse, status_code=status.HTTP_201_CREATED)
def add_movie(
    payload: MovieCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    movie = Movie(**payload.model_dump())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    db.delete(movie)
    db.commit()


# --- Theatres ---

@router.post("/theatres", response_model=TheatreResponse, status_code=status.HTTP_201_CREATED)
def add_theatre(
    payload: TheatreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    theatre = Theatre(**payload.model_dump())
    db.add(theatre)
    db.commit()
    db.refresh(theatre)
    return theatre


@router.get("/theatres", response_model=List[TheatreResponse])
def list_theatres(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(Theatre).all()


# --- Screens ---

@router.post("/screens", response_model=ScreenResponse, status_code=status.HTTP_201_CREATED)
def add_screen(
    payload: ScreenCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    theatre = db.query(Theatre).filter(Theatre.id == payload.theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")
    screen = Screen(**payload.model_dump())
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return screen


@router.patch("/screens/{screen_id}/assign-movie", response_model=ScreenResponse)
def assign_movie_to_screen(
    screen_id: int,
    payload: ScreenAssignMovie,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    screen = db.query(Screen).filter(Screen.id == screen_id).first()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    screen.current_movie_id = payload.movie_id
    db.commit()
    db.refresh(screen)
    return screen


# --- Seats ---

@router.post("/screens/{screen_id}/seats", response_model=List[SeatResponse], status_code=status.HTTP_201_CREATED)
def add_seats(
    screen_id: int,
    payload: SeatBulkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    screen = db.query(Screen).filter(Screen.id == screen_id).first()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    seats = []
    for seat_data in payload.seats:
        seat = Seat(screen_id=screen_id, **seat_data.model_dump())
        db.add(seat)
        seats.append(seat)

    db.commit()
    for seat in seats:
        db.refresh(seat)
    return seats


# --- Shows ---

@router.post("/shows", response_model=ShowResponse, status_code=status.HTTP_201_CREATED)
def add_show(
    payload: ShowCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    screen = db.query(Screen).filter(Screen.id == payload.screen_id).first()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    show = Show(**payload.model_dump())
    db.add(show)
    db.flush()  # get show.id before commit

    # Create seat availability entries for all seats in this screen
    seats = db.query(Seat).filter(Seat.screen_id == payload.screen_id).all()
    for seat in seats:
        availability = SeatAvailability(
            show_id=show.id,
            seat_id=seat.id,
            status=SeatStatus.AVAILABLE,
        )
        db.add(availability)

    db.commit()
    db.refresh(show)
    return show


@router.get("/shows", response_model=List[ShowResponse])
def list_shows(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(Show).all()
