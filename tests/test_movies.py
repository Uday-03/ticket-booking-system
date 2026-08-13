"""
Unit tests for movies module.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.movies.models import Movie


class TestGetMovies:
    """Test movie retrieval endpoints."""
    
    def test_list_all_movies(
        self,
        client: TestClient,
        user_token: str,
        test_movie: Movie,
        db: Session,
    ):
        """Test listing all movies."""
        # Add another movie
        movie2 = Movie(
            name="Another Movie",
            language="Tamil",
            duration_minutes=130,
            rating=7.0,
            description="Another great movie",
        )
        db.add(movie2)
        db.commit()
        
        response = client.get(
            "/movies",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert any(m["name"] == test_movie.name for m in data)
        assert any(m["name"] == "Another Movie" for m in data)


    def test_list_movies_no_movies(
        self,
        client: TestClient,
        user_token: str,
        db: Session,
    ):
        """Test listing movies when none exist."""
        # Delete all movies
        db.query(Movie).delete()
        db.commit()
        
        response = client.get(
            "/movies",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


    def test_get_movie_by_id(
        self,
        client: TestClient,
        user_token: str,
        test_movie: Movie,
    ):
        """Test getting a movie by ID."""
        response = client.get(
            f"/movies/{test_movie.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_movie.id
        assert data["name"] == test_movie.name
        assert data["language"] == test_movie.language
        assert data["duration_minutes"] == test_movie.duration_minutes
        assert data["rating"] == test_movie.rating
        assert data["description"] == test_movie.description


    def test_get_nonexistent_movie(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test getting non-existent movie returns 404."""
        response = client.get(
            "/movies/99999",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404


class TestMovieAccess:
    """Test movie endpoints."""
    
    def test_get_movies_public(
        self,
        client: TestClient,
        test_movie: Movie,
    ):
        """Test accessing movie endpoints is public (no auth required)."""
        response = client.get("/movies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


    def test_get_movie_detail_public(
        self,
        client: TestClient,
        test_movie: Movie,
    ):
        """Test accessing movie detail is public (no auth required)."""
        response = client.get(f"/movies/{test_movie.id}")
        assert response.status_code == 200
