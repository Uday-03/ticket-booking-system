# Ticket Booking System

A movie ticket booking backend built with **FastAPI**, **MySQL**, **Redis**, and **Celery**.

## Tech Stack

| Layer | Tool |
|---|---|
| Framework | FastAPI |
| Database | MySQL + SQLAlchemy ORM |
| Migrations | Alembic |
| Cache | Redis |
| Async Jobs | Celery + Redis |
| Auth | JWT (role-based: user / admin) |

## Architecture

Modular monolith with 5 modules:
- `auth` — register, login, JWT
- `movies` — browse movies
- `admin` — manage movies, theatres, screens, seats, shows
- `booking` — seat selection, block, confirm, cancel
- `payment` — async payment processing via Celery

## Setup

### 1. Clone and create virtual environment
```bash
git clone https://github.com/Uday-03/ticket-booking-system.git
cd ticket-booking-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your MySQL credentials and secret key
```

### 3. Create MySQL database
```sql
CREATE DATABASE ticket_booking;
```

### 4. Run migrations
```bash
alembic upgrade head
```

### 5. Start Redis (required for cache + Celery)
```bash
redis-server
```

### 6. Start Celery worker
```bash
celery -A celery_worker worker --loglevel=info -Q payment
```

### 7. Start Celery beat (for seat expiry)
```bash
celery -A celery_worker beat --loglevel=info
```

### 8. Run the API
```bash
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

## Key Features

- JWT auth with separate user and admin roles
- Admin manages theatres, screens, seat pricing, movies, shows
- Seat blocking with 10-minute timeout
- Row-level DB locking to prevent double booking
- Async payment processing via Celery
- Automatic seat release on payment failure or timeout
- Ticket generation on booking confirmation

## API Endpoints

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | /auth/register | Public | Register user |
| POST | /auth/login | Public | Login |
| GET | /movies | User | List all movies |
| GET | /movies/{id} | User | Get movie details |
| POST | /admin/movies | Admin | Add movie |
| DELETE | /admin/movies/{id} | Admin | Remove movie |
| POST | /admin/theatres | Admin | Add theatre |
| POST | /admin/screens | Admin | Add screen |
| PATCH | /admin/screens/{id}/assign-movie | Admin | Assign movie to screen |
| POST | /admin/screens/{id}/seats | Admin | Add seats to screen |
| POST | /admin/shows | Admin | Create show |
| GET | /booking/shows/{id}/seats | User | View seat availability |
| POST | /booking/block-seats | User | Block seats (10 min hold) |
| POST | /booking/confirm/{booking_id} | User | Confirm and pay |
| POST | /booking/cancel/{booking_id} | User | Cancel booking |
| GET | /booking/my-bookings | User | View my bookings |
| GET | /booking/ticket/{booking_id} | User | Get ticket |
| GET | /payment/{booking_id} | User | Check payment status |
