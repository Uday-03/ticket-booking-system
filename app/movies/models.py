from sqlalchemy import Column, Integer, String, Float, Text
from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    language = Column(String(50), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    rating = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
