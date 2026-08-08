import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Date, Time
from sqlalchemy.orm import relationship
from app.database import Base


class Theatre(Base):
    __tablename__ = "theatres"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(300), nullable=False)

    screens = relationship("Screen", back_populates="theatre")


class Screen(Base):
    __tablename__ = "screens"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    theatre_id = Column(Integer, ForeignKey("theatres.id"), nullable=False)
    current_movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)

    theatre = relationship("Theatre", back_populates="screens")
    seats = relationship("Seat", back_populates="screen")
    shows = relationship("Show", back_populates="screen")


class SeatType(str, enum.Enum):
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False)
    seat_number = Column(String(10), nullable=False)
    seat_type = Column(Enum(SeatType), nullable=False)
    price = Column(Float, nullable=False)

    screen = relationship("Screen", back_populates="seats")


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    show_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    screen = relationship("Screen", back_populates="shows")
