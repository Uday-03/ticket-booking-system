"""
Unit tests for admin module.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.admin.models import Theatre, Screen, Seat, Show
from app.movies.models import Movie


class TestAdminMovies:
    """Test admin movie management."""
    
    def test_add_movie_success(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test adding a movie as admin."""
        response = client.post(
            "/admin/movies",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Movie",
                "language": "Hindi",
                "duration_minutes": 150,
                "rating": 7.5,
                "description": "A great movie",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Movie"
        assert data["language"] == "Hindi"
        assert "id" in data


    def test_add_movie_without_admin_role(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test regular user cannot add movie."""
        response = client.post(
            "/admin/movies",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "name": "New Movie",
                "language": "Hindi",
                "duration_minutes": 150,
                "rating": 7.5,
                "description": "A great movie",
            },
        )
        assert response.status_code == 403


    def test_delete_movie_success(
        self,
        client: TestClient,
        admin_token: str,
        test_movie: Movie,
    ):
        """Test deleting a movie as admin."""
        response = client.delete(
            f"/admin/movies/{test_movie.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200


    def test_delete_nonexistent_movie(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test deleting non-existent movie fails."""
        response = client.delete(
            "/admin/movies/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestAdminTheatres:
    """Test admin theatre management."""
    
    def test_add_theatre_success(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test adding a theatre as admin."""
        response = client.post(
            "/admin/theatres",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "PVR Cinema",
                "location": "New Delhi",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PVR Cinema"
        assert "id" in data


    def test_list_theatres(
        self,
        client: TestClient,
        admin_token: str,
        test_theatre: Theatre,
    ):
        """Test listing theatres."""
        response = client.get(
            "/admin/theatres",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(t["id"] == test_theatre.id for t in data)


class TestAdminScreens:
    """Test admin screen management."""
    
    def test_add_screen_success(
        self,
        client: TestClient,
        admin_token: str,
        test_theatre: Theatre,
    ):
        """Test adding a screen to theatre."""
        response = client.post(
            "/admin/screens",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Screen 2",
                "theatre_id": test_theatre.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Screen 2"
        assert data["theatre_id"] == test_theatre.id


    def test_add_screen_to_nonexistent_theatre(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test adding screen to non-existent theatre fails."""
        response = client.post(
            "/admin/screens",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Screen X",
                "theatre_id": 99999,
            },
        )
        assert response.status_code == 404


    def test_assign_movie_to_screen(
        self,
        client: TestClient,
        admin_token: str,
        test_screen: Screen,
        test_movie: Movie,
    ):
        """Test assigning a movie to a screen."""
        response = client.patch(
            f"/admin/screens/{test_screen.id}/assign-movie",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"movie_id": test_movie.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_movie_id"] == test_movie.id


class TestAdminSeats:
    """Test admin seat management."""
    
    def test_add_seats_to_screen(
        self,
        client: TestClient,
        admin_token: str,
        test_screen: Screen,
        db: Session,
    ):
        """Test bulk adding seats to a screen."""
        response = client.post(
            f"/admin/screens/{test_screen.id}/seats",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "seat_rows": [
                    {"row": "A", "seat_type": "SILVER", "price": 200.0},
                    {"row": "B", "seat_type": "GOLD", "price": 300.0},
                ],
                "seats_per_row": 5,
            },
        )
        assert response.status_code == 201
        
        # Verify seats were created
        seats = db.query(Seat).filter(Seat.screen_id == test_screen.id).all()
        assert len(seats) == 10  # 2 rows x 5 seats


    def test_add_seats_to_nonexistent_screen(
        self,
        client: TestClient,
        admin_token: str,
    ):
        """Test adding seats to non-existent screen fails."""
        response = client.post(
            "/admin/screens/99999/seats",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "seat_rows": [
                    {"row": "A", "seat_type": "SILVER", "price": 200.0},
                ],
                "seats_per_row": 5,
            },
        )
        assert response.status_code == 404


class TestAdminShows:
    """Test admin show management."""
    
    def test_create_show_success(
        self,
        client: TestClient,
        admin_token: str,
        test_screen: Screen,
        test_movie: Movie,
        db: Session,
    ):
        """Test creating a show."""
        response = client.post(
            "/admin/shows",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "screen_id": test_screen.id,
                "movie_id": test_movie.id,
                "show_date": "2026-08-20",
                "start_time": "18:00",
                "end_time": "20:00",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["screen_id"] == test_screen.id
        assert data["movie_id"] == test_movie.id
        
        # Verify seat availability was created
        show = db.query(Show).filter(Show.id == data["id"]).first()
        from app.booking.models import SeatAvailability
        availabilities = db.query(SeatAvailability).filter(
            SeatAvailability.show_id == show.id
        ).all()
        assert len(availabilities) > 0


    def test_create_show_nonexistent_screen(
        self,
        client: TestClient,
        admin_token: str,
        test_movie: Movie,
    ):
        """Test creating show for non-existent screen fails."""
        response = client.post(
            "/admin/shows",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "screen_id": 99999,
                "movie_id": test_movie.id,
                "show_date": "2026-08-20",
                "start_time": "18:00",
                "end_time": "20:00",
            },
        )
        assert response.status_code == 404


    def test_list_shows(
        self,
        client: TestClient,
        admin_token: str,
        test_show: Show,
    ):
        """Test listing all shows."""
        response = client.get(
            "/admin/shows",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["id"] == test_show.id for s in data)


class TestAdminRoleValidation:
    """Test admin role validation for all admin endpoints."""
    
    def test_regular_user_cannot_access_admin_endpoints(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test regular user gets 403 for admin endpoints."""
        endpoints = [
            ("POST", "/admin/movies", {"name": "Movie"}),
            ("POST", "/admin/theatres", {"name": "Theatre", "location": "Loc"}),
            ("POST", "/admin/screens", {"name": "Screen", "theatre_id": 1}),
        ]
        
        for method, endpoint, data in endpoints:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {user_token}"},
                json=data,
            )
            assert response.status_code == 403, f"Failed for {endpoint}"
