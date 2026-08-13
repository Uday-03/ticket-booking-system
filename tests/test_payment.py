"""
Unit tests for payment module.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.booking.models import Booking, BookingStatus
from app.payment.models import Payment, PaymentStatus


class TestGetPaymentStatus:
    """Test payment status retrieval."""
    
    def test_get_payment_status_success(
        self,
        client: TestClient,
        user_token: str,
        test_payment: Payment,
    ):
        """Test retrieving payment status."""
        response = client.get(
            f"/payment/{test_payment.booking_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["booking_id"] == test_payment.booking_id
        assert data["status"] == "PENDING"
        assert data["amount"] == test_payment.amount


    def test_get_payment_status_not_found(
        self,
        client: TestClient,
        user_token: str,
    ):
        """Test retrieving payment for non-existent booking fails."""
        response = client.get(
            "/payment/99999",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404


    def test_get_payment_other_user(
        self,
        client: TestClient,
        admin_token: str,
        test_payment: Payment,
    ):
        """Test retrieving another user's payment fails."""
        response = client.get(
            f"/payment/{test_payment.booking_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestPaymentStatus:
    """Test payment status transitions."""
    
    def test_payment_pending_to_success(
        self,
        db: Session,
        test_payment: Payment,
    ):
        """Test payment status transition from PENDING to SUCCESS."""
        assert test_payment.status == PaymentStatus.PENDING
        
        test_payment.status = PaymentStatus.SUCCESS
        db.commit()
        db.refresh(test_payment)
        
        assert test_payment.status == PaymentStatus.SUCCESS


    def test_payment_pending_to_failed(
        self,
        db: Session,
        test_payment: Payment,
    ):
        """Test payment status transition from PENDING to FAILED."""
        assert test_payment.status == PaymentStatus.PENDING
        
        test_payment.status = PaymentStatus.FAILED
        db.commit()
        db.refresh(test_payment)
        
        assert test_payment.status == PaymentStatus.FAILED


    def test_payment_success_to_refunded(
        self,
        db: Session,
        test_payment: Payment,
    ):
        """Test payment refund."""
        test_payment.status = PaymentStatus.SUCCESS
        db.commit()
        
        test_payment.status = PaymentStatus.REFUNDED
        db.commit()
        db.refresh(test_payment)
        
        assert test_payment.status == PaymentStatus.REFUNDED


class TestPaymentBookingRelationship:
    """Test payment and booking relationship."""
    
    def test_payment_booking_association(
        self,
        test_booking: Booking,
        test_payment: Payment,
    ):
        """Test payment is correctly associated with booking."""
        assert test_payment.booking_id == test_booking.id


    def test_payment_amount_matches_booking(
        self,
        test_booking: Booking,
        test_payment: Payment,
    ):
        """Test payment amount matches booking total."""
        assert test_payment.amount == test_booking.total_amount


class TestPaymentCancellation:
    """Test payment-related cancellation scenarios."""
    
    def test_cancel_with_successful_payment_refunds(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        test_payment: Payment,
        db: Session,
    ):
        """Test that cancelling a booking with successful payment refunds it."""
        # Mark payment as successful
        test_payment.status = PaymentStatus.SUCCESS
        db.commit()
        
        # Cancel booking
        response = client.post(
            f"/booking/cancel/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        
        # Verify payment is refunded
        db.refresh(test_payment)
        assert test_payment.status == PaymentStatus.REFUNDED


    def test_cancel_with_pending_payment_no_refund(
        self,
        client: TestClient,
        user_token: str,
        test_booking: Booking,
        test_payment: Payment,
        db: Session,
    ):
        """Test that cancelling with pending payment doesn't create refund."""
        assert test_payment.status == PaymentStatus.PENDING
        
        response = client.post(
            f"/booking/cancel/{test_booking.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        
        # Payment should still be pending
        db.refresh(test_payment)
        assert test_payment.status == PaymentStatus.PENDING
