"""
Unit tests for booking module — critical path.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.booking.models import (
    SeatAvailability, SeatStatus, Booking, BookingStatus, BookingSeat, Ticket
)
from app.admin.models import Seat, Show


class TestBlockSeats:
    """Test seat blocking functionality."""
    
    def test_block_seats_success(
        self,
        client: TestClient,
        user_token: str,
        test_show: Show,
        test_seats: list[Seat],
        db: Session,
    ):
        """Test successful seat blocking."""
        # Create seat availability
        for seat in test_seats:
            av = SeatAvailability(
                show_id=test_show.id,
                seat_id=seat.id,
                status=SeatStatus.AVAILABLE,
            )
            db.add(av)
        db.commit()
        
        # Block seats A1, A2
        response = client.post(
            "/booking/block-seats",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "show_id": test_show.id,
                "seat_ids": [test_seats[0].id, test_seats[1].id],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "booking_id" in data
        assert data["total_amount"] == test_seats[0].price + test_seats[1].price
        
        # Verify seats are blocked
        availabilities = db.query(SeatAvailability).filter(
            SeatAvailability.show_id == test_show.id,
            SeatAvailability.seat_id.in_([test_seats[0].id, test_seats[1].id]),
        ).all()
        assert all(av.status == SeatStatus.BLOCKED for av in availabilities)


    def test_block_already_blocked_seat(
        self,
        client: TestClient,
        user_token: str,
        test_show: Show,
        test_seats: list[Seat],
        db: Session,
    ):
        """Test blocking a seat that's already blocked fails."""
        # Create seat availability with one blocked
        for i, seat in enumerate(test_seats):
            status = SeatStatus.BLOCKED if i == 0 else SeatStatus.AVAILABLE
            av = SeatAvailability(
                show_id=test_show.id,
                seat_id=seat.id,
                status=status,
            )
            db.add(av)
        db.commit()
        
        # Try to block the already-blocked seat
        response = client.post(
            "/booking/block-seats",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "show_id": test_show.id,
                "seat_ids": [test_seats[0].id],
            },
        )
        assert response.status_code == 409
        assert "not available" in response.json()["detail"].lower()


    def test_block_seats_without_auth(
        self,
        client: TestClient,
        test_show: Show,
        test_seats: list[Seat],
        db: Session,
    ):
        """Test blocking seats without authentication fails."""
        for seat in test_seats:
            av = SeatAvailability(
                show_id=test_show.id,
                seat_id=seat.id,
                status=SeatStatus.AVAILABLE,
            )
            db.add(av)
        db.commit()
        
        response = client.post(
            "/booking/block-seats",
            json={
                "show_id": test_show.id,
                "seat_ids": [test_seats[0].id],
            },
        )
        assert response.status_code == 403


    def test_block_nonexistent_seat(
        self,
        client: TestClient,
        user_token: str,
        test_show: Show,
        test_seats: list[Seat],
        db: Session,
    ):
        """Test blocking non-existent seat fails."""
        for seat in test_seats:
            av = SeatAvailability(
                show_id=test_show.id,
                seat_id=seat.id,
                status=SeatStatus.AVAILABLE,
            )
            db.add(av)
        db.commit()
        
        response = client.post(
            "/booking/block-seats",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "show_id": test_show.id,
                "seat_ids": [99999],  # Non-existent seat
            },
        )
        assert response.status_code == 400


class TestConfirmBooking:
    """Test booking confirmation and payment flow."""
    
    def test_confirm_booking_success(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        db: Session,
    ):
        """Test successful booking confirmation (async payment triggered)."""
        response = client.post(
            f"/booking/confirm/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["booking_id"] == test_booking.id
        assert data["status"] == "PENDING"  # Payment being processed
        assert "payment" in data["message"].lower() or "processing" in data["message"].lower()


    def test_confirm_booking_not_found(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test confirming non-existent booking fails."""
        response = client.post(
            "/booking/confirm/99999",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404


    def test_confirm_already_confirmed_booking(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        db: Session,
    ):
        """Test confirming already confirmed booking fails."""
        # Mark booking as confirmed
        test_booking.status = BookingStatus.CONFIRMED
        db.commit()
        
        response = client.post(
            f"/booking/confirm/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()


    def test_confirm_other_user_booking(
        self,
        client: TestClient,
        admin_token: str,  # Using admin token (different user)
        test_booking: Booking,
    ):
        """Test confirming another user's booking fails."""
        response = client.post(
            f"/booking/confirm/{test_booking.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestCancelBooking:
    """Test booking cancellation."""
    
    def test_cancel_booking_success(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        test_seats: list[Seat],
        db: Session,
    ):
        """Test successful booking cancellation."""
        # Block the seats for the booking
        for seat in test_seats[:2]:
            av = SeatAvailability(
                show_id=test_booking.show_id,
                seat_id=seat.id,
                status=SeatStatus.BLOCKED,
                blocked_by=test_booking.user_id,
            )
            db.add(av)
        db.commit()
        
        response = client.post(
            f"/booking/cancel/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"
        
        # Verify seats are released
        availabilities = db.query(SeatAvailability).filter(
            SeatAvailability.show_id == test_booking.show_id,
            SeatAvailability.seat_id.in_([test_seats[0].id, test_seats[1].id]),
        ).all()
        assert all(av.status == SeatStatus.AVAILABLE for av in availabilities)


    def test_cancel_already_cancelled_booking(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        db: Session,
    ):
        """Test cancelling already cancelled booking fails."""
        test_booking.status = BookingStatus.CANCELLED
        db.commit()
        
        response = client.post(
            f"/booking/cancel/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400


    def test_cancel_other_user_booking(
        self,
        client: TestClient,
        admin_token: str,
        test_booking: Booking,
    ):
        """Test cancelling another user's booking fails."""
        response = client.post(
            f"/booking/cancel/{test_booking.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestGetBookingTicket:
    """Test ticket retrieval."""
    
    def test_get_ticket_success(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        test_ticket: Ticket,
        db: Session,
    ):
        """Test successful ticket retrieval."""
        # Mark booking as confirmed (required for ticket retrieval)
        test_booking.status = BookingStatus.CONFIRMED
        db.commit()
        
        response = client.get(
            f"/booking/ticket/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["booking_id"] == test_booking.id
        assert data["movie_name"] == test_ticket.movie_name
        assert data["screen_name"] == test_ticket.screen_name


    def test_get_ticket_pending_booking(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
    ):
        """Test getting ticket for pending booking fails."""
        response = client.get(
            f"/booking/ticket/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 400
        assert "confirmed" in response.json()["detail"].lower()


    def test_get_ticket_not_found(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test getting ticket for non-existent booking fails."""
        response = client.get(
            "/booking/ticket/99999",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404


class TestGetMyBookings:
    """Test retrieving user's bookings."""
    
    def test_get_my_bookings_success(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
    ):
        """Test retrieving user's bookings."""
        response = client.get(
            "/booking/my-bookings",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["id"] == test_booking.id


    def test_get_my_bookings_empty(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test retrieving bookings for user with no bookings."""
        response = client.get(
            "/booking/my-bookings",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestGetSeatAvailability:
    """Test seat availability retrieval."""
    
    def test_get_seat_availability_success(
        self,
        client: TestClient,
        user_token: str,
        test_show: Show,
        test_seat_availability: list[SeatAvailability],
    ):
        """Test retrieving seat availability."""
        response = client.get(
            f"/booking/shows/{test_show.id}/seats",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(test_seat_availability)
        assert all(seat["status"] == "AVAILABLE" for seat in data)


    def test_get_seat_availability_nonexistent_show(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test retrieving seat availability for non-existent show fails."""
        response = client.get(
            "/booking/shows/99999/seats",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404


class TestDoubleSeatBookingPrevention:
    """Test double booking prevention with row-level locking."""
    
    def test_concurrent_seat_block_attempt(
        self,
        client: TestClient,
        user_token: str,
        test_user: Session,
        test_show: Show,
        test_seats: list[Seat],
        db: Session,
    ):
        """
        Test that second user cannot block a seat already blocked by first user.
        This simulates concurrent access.
        """
        # Create seat availability
        for seat in test_seats:
            av = SeatAvailability(
                show_id=test_show.id,
                seat_id=seat.id,
                status=SeatStatus.AVAILABLE,
            )
            db.add(av)
        db.commit()
        
        # First user blocks seat A1
        response1 = client.post(
            "/booking/block-seats",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "show_id": test_show.id,
                "seat_ids": [test_seats[0].id],
            },
        )
        assert response1.status_code == 200
        
        # Second user tries to block the same seat
        # (Using same token for simplicity; in real scenario would be different user)
        response2 = client.post(
            "/booking/block-seats",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "show_id": test_show.id,
                "seat_ids": [test_seats[0].id],
            },
        )
        # Should fail because seat is already blocked
        assert response2.status_code == 409
