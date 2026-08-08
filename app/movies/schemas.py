from pydantic import BaseModel
from typing import Optional


class MovieResponse(BaseModel):
    id: int
    name: str
    language: str
    duration_minutes: int
    rating: float
    description: Optional[str] = None

    class Config:
        from_attributes = True
