# Ticket Booking System — Progress Tracker

## Project Info
- **Repo:** https://github.com/Uday-03/ticket-booking-system
- **Local path:** ~/MovieBookingApp/ticket-booking-system
- **Started:** 2026-08-08

---

## Tech Stack (Agreed)

| Layer | Choice |
|---|---|
| Language | Python |
| Framework | FastAPI |
| ORM | SQLAlchemy |
| Database | MySQL |
| Migrations | Alembic |
| Cache | Redis |
| Async Jobs | Celery + Redis |
| Auth | JWT (role-based: user / admin) |
| Architecture | Modular Monolith |

---

## Architecture Decisions (Agreed)

| Topic | Decision |
|---|---|
| Architecture | Modular Monolith |
| Auth | JWT with role-based access (user / admin) |
| Admin | Manages pricing, theatre, screen-movie assignment |
| Pricing | Final price, no tax/extra charges |
| Cache | Redis for seat availability |
| Seat block timeout | 10 minutes |
| Invoice | Removed — only Ticket entity |
| Screen | 1 movie at a time, multiple time-slot shows |
| Payment | Async via Celery + Redis message queue |
| Double booking prevention | DB row-level lock (SQLAlchemy with_for_update) |
| Seat expiry | Celery beat job runs every 60 seconds to release expired blocked seats |
| Notifications | Deferred to future enhancement |
| QR code on ticket | Deferred to future enhancement |

---

## Modules

| Module | Responsibility |
|---|---|
| `auth` | Register, login, JWT issue, role guards |
| `movies` | Browse movies, get movie by id (user-facing) |
| `admin` | Manage movies, theatres, screens, seats, shows |
| `booking` | Seat availability, block seats, confirm, cancel, ticket retrieval |
| `payment` | Async payment processing, payment status |

---

## API Endpoints (Designed)

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | /auth/register | Public | Register user |
| POST | /auth/login | Public | Login, returns JWT |
| GET | /movies | User | List all movies |
| GET | /movies/{id} | User | Get movie details |
| POST | /admin/movies | Admin | Add movie |
| DELETE | /admin/movies/{id} | Admin | Remove movie |
| POST | /admin/theatres | Admin | Add theatre |
| GET | /admin/theatres | Admin | List theatres |
| POST | /admin/screens | Admin | Add screen to theatre |
| PATCH | /admin/screens/{id}/assign-movie | Admin | Assign movie to screen |
| POST | /admin/screens/{id}/seats | Admin | Bulk add seats to screen |
| POST | /admin/shows | Admin | Create show (auto-creates seat availability) |
| GET | /admin/shows | Admin | List all shows |
| GET | /booking/shows/{id}/seats | User | View seat availability for a show |
| POST | /booking/block-seats | User | Block seats (10 min hold, row-level lock) |
| POST | /booking/confirm/{booking_id} | User | Confirm booking (triggers async payment) |
| POST | /booking/cancel/{booking_id} | User | Cancel booking, release seats |
| GET | /booking/my-bookings | User | View all bookings for logged-in user |
| GET | /booking/ticket/{booking_id} | User | Get ticket for confirmed booking |
| GET | /payment/{booking_id} | User | Check payment status |

---

## Database Schema (Implemented)

| Table | Key Columns |
|---|---|
| `users` | id, name, email, phone, password_hash, role (user/admin) |
| `movies` | id, name, language, duration_minutes, rating, description |
| `theatres` | id, name, location |
| `screens` | id, name, theatre_id, current_movie_id |
| `seats` | id, screen_id, seat_number, seat_type (SILVER/GOLD/PLATINUM), price |
| `shows` | id, screen_id, movie_id, show_date, start_time, end_time |
| `seat_availability` | id, show_id, seat_id, status (AVAILABLE/BLOCKED/BOOKED), blocked_by, blocked_at |
| `bookings` | id, user_id, show_id, total_amount, status (PENDING/CONFIRMED/CANCELLED) |
| `booking_seats` | id, booking_id, seat_id |
| `tickets` | id, booking_id, movie_name, screen_name, show_date, show_time, seat_details, total_amount |
| `payments` | id, booking_id, amount, status (PENDING/SUCCESS/FAILED/REFUNDED), payment_type |

---

## Progress Log

### Session 1 — 2026-08-08

#### Requirements Discussion
- [x] Analyzed design diagram from Excalidraw (exported as PNG)
- [x] Confirmed requirements: movie ticket booking backend (BookMyShow-like)
- [x] No tax/extra charges — price shown is final price
- [x] Admin decides seat pricing, theatre setup, screen-movie assignment
- [x] Seat block timeout: 10 minutes
- [x] Removed Invoice entity — only Ticket
- [x] Screen plays 1 movie at a time, supports multiple time-slot shows
- [x] Payment: async via message queue (Celery)
- [x] Tech stack finalized: Python + FastAPI + MySQL + Redis + Celery
- [x] Architecture: Modular Monolith
- [x] Auth: JWT with separate user and admin roles
- [x] Ticket contents: booking_id, movie_name, screen_name, show_date, show_time, seat_details, total_amount

#### Setup
- [x] Git repo created: https://github.com/Uday-03/ticket-booking-system
- [x] Local directory: ~/MovieBookingApp/ticket-booking-system
- [x] Git remote connected and initial commit pushed

#### Code Scaffolded
- [x] `requirements.txt` — all dependencies pinned
- [x] `.env` — environment variables template
- [x] `.gitignore`
- [x] `app/config.py` — pydantic-settings config
- [x] `app/database.py` — SQLAlchemy engine + session + Base
- [x] `app/main.py` — FastAPI app, all routers registered
- [x] `app/auth/models.py` — User model with role enum
- [x] `app/auth/schemas.py` — register, login, token schemas
- [x] `app/auth/utils.py` — JWT create/decode, password hash, auth dependencies
- [x] `app/auth/router.py` — POST /auth/register, POST /auth/login
- [x] `app/movies/models.py` — Movie model
- [x] `app/movies/schemas.py` — MovieResponse schema
- [x] `app/movies/router.py` — GET /movies, GET /movies/{id}
- [x] `app/admin/models.py` — Theatre, Screen, Seat, Show models
- [x] `app/admin/schemas.py` — all admin request/response schemas
- [x] `app/admin/router.py` — full admin CRUD endpoints
- [x] `app/booking/models.py` — SeatAvailability, Booking, BookingSeat, Ticket models
- [x] `app/booking/schemas.py` — booking schemas
- [x] `app/booking/router.py` — all booking endpoints
- [x] `app/booking/tasks.py` — Celery periodic task for expired seat release
- [x] `app/payment/models.py` — Payment model with status/type enums
- [x] `app/payment/schemas.py` — PaymentResponse schema
- [x] `app/payment/celery_app.py` — Celery app + beat schedule config
- [x] `app/payment/tasks.py` — async payment processing task
- [x] `app/payment/router.py` — GET /payment/{booking_id}
- [x] `celery_worker.py` — Celery worker entry point
- [x] `alembic/` — initialized, env.py configured with all models
- [x] `README.md` — setup instructions + full API reference
- [x] Import check passed: `from app.main import app` ✅

---

## Pending / Next Steps

### Immediate (next session)
- [ ] Update `.env` with real MySQL password and SECRET_KEY
- [ ] Create MySQL database: `CREATE DATABASE ticket_booking;`
- [ ] Generate and run first Alembic migration:
  ```bash
  alembic revision --autogenerate -m "initial"
  alembic upgrade head
  ```
- [ ] Start Redis server
- [ ] Run the API: `uvicorn app.main:app --reload`
- [ ] Test all endpoints via Swagger UI at http://localhost:8000/docs

### Future Enhancements
- [ ] Email/SMS notifications on booking confirmation and cancellation
- [ ] QR code generation on ticket
- [ ] Deploy to AWS (EC2 + RDS + ElastiCache) for live resume demo
- [ ] Redis caching layer for seat availability reads
- [ ] Real payment gateway integration (Razorpay/Stripe)
- [ ] Unit and integration tests
