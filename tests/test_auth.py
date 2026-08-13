"""
Unit tests for auth module.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.auth.utils import hash_password, verify_password, decode_token, create_access_token


class TestAuthRegister:
    """Test user registration."""
    
    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "phone": "7777777777",
                "password": "secure123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["role"] == "user"
        assert "password" not in data


    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration fails with duplicate email."""
        response = client.post(
            "/auth/register",
            json={
                "name": "Another User",
                "email": test_user.email,
                "phone": "7777777777",
                "password": "secure123",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()


    def test_register_missing_fields(self, client: TestClient):
        """Test registration fails with missing fields."""
        response = client.post(
            "/auth/register",
            json={
                "email": "incomplete@example.com",
                # missing name, phone, password
            },
        )
        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Test user login."""
    
    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


    def test_login_invalid_credentials(self, client: TestClient, test_user: User):
        """Test login fails with invalid password."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


    def test_login_user_not_found(self, client: TestClient):
        """Test login fails with non-existent user."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401


class TestPasswordHashing:
    """Test password hashing utility functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 20
    

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False


class TestJWTToken:
    """Test JWT token creation and decoding."""
    
    def test_create_and_decode_token(self, test_user: User):
        """Test creating and decoding JWT token."""
        token = create_access_token(test_user.id, test_user.role)
        decoded = decode_token(token)
        
        assert decoded.user_id == test_user.id
        assert decoded.role == UserRole.user


    def test_decode_invalid_token(self):
        """Test decoding invalid token raises error."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            decode_token("invalid.token.here")


class TestAuthDependencies:
    """Test auth dependency functions."""
    
    def test_get_current_user_with_valid_token(self, client: TestClient, user_token: str):
        """Test accessing protected endpoint with valid token."""
        # Use a protected endpoint like booking
        response = client.get(
            "/booking/my-bookings",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200


    def test_get_current_user_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token."""
        # Use a protected endpoint  that requires auth
        response = client.get("/booking/my-bookings")
        assert response.status_code == 403


    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token."""
        response = client.get(
            "/booking/my-bookings",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 403
