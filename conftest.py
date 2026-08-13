"""
Global pytest configuration and fixtures.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.auth.models import User, UserRole
from app.movies.models import Movie
from app.admin.models import Theatre, Screen, Seat, SeatType, Show
from app.booking.models import Booking, BookingStatus, BookingSeat, SeatAvailability, SeatStatus, Ticket
from app.payment.models import Payment, PaymentStatus, PaymentType
from app.auth.utils import hash_password, create_access_token


# Create a shared in-memory SQLite database for all tests in a session
@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped engine with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables once
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(test_engine):
    """Function-scoped session that clears tables between tests."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    
    yield session
    
    # Clean up all tables after each test
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture(scope="function")
def client(db):
    """Test client with database dependency overridden."""
    def get_db_override():
        yield db
    
    app.dependency_overrides[get_db] = get_db_override
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================================================
# Test fixtures
# ============================================================================

@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test regular user."""
    user = User(
        name="Test User",
        email="user@example.com",
        phone="9999999999",
        password_hash=hash_password("password123"),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db: Session) -> User:
    """Create a test admin user."""
    user = User(
        name="Admin User",
        email="admin@example.com",
        phone="8888888888",
        password_hash=hash_password("admin123"),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """Generate JWT token for test user."""
    return create_access_token(test_user.id, test_user.role)


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """Generate JWT token for test admin."""
    return create_access_token(test_admin.id, test_admin.role)


@pytest.fixture
def test_movie(db: Session) -> Movie:
    """Create a test movie."""
    movie = Movie(
        name="Test Movie",
        language="English",
        duration_minutes=120,
        rating=8.0,
        description="A great test movie",
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@pytest.fixture
def test_theatre(db: Session) -> Theatre:
    """Create a test theatre."""
    theatre = Theatre(
        name="Test Theatre",
        location="Test Location",
    )
    db.add(theatre)
    db.commit()
    db.refresh(theatre)
    return theatre


@pytest.fixture
def test_screen(db: Session, test_theatre: Theatre, test_movie: Movie) -> Screen:
    """Create a test screen with movie assigned."""
    screen = Screen(
        name="Screen 1",
        theatre_id=test_theatre.id,
        current_movie_id=test_movie.id,
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return screen


@pytest.fixture
def test_seats(db: Session, test_screen: Screen) -> list[Seat]:
    """Create test seats for a screen (3x3 grid: 9 seats)."""
    seats = []
    seat_types = [SeatType.SILVER, SeatType.GOLD, SeatType.PLATINUM]
    prices = [200.0, 300.0, 400.0]
    
    for row in range(3):
        for col in range(3):
            seat = Seat(
                screen_id=test_screen.id,
                seat_number=f"{chr(65 + row)}{col + 1}",  # A1, A2, A3, B1, B2, B3, C1, C2, C3
                seat_type=seat_types[row],
                price=prices[row],
            )
            seats.append(seat)
            db.add(seat)
    
    db.commit()
    for seat in seats:
        db.refresh(seat)
    return seats


@pytest.fixture
def test_show(db: Session, test_screen: Screen, test_movie: Movie) -> Show:
    """Create a test show."""
    from datetime import date, time
    show = Show(
        screen_id=test_screen.id,
        movie_id=test_movie.id,
        show_date=date.today(),
        start_time=time(14, 0),
        end_time=time(16, 0),
    )
    db.add(show)
    db.commit()
    db.refresh(show)
    return show


@pytest.fixture
def test_seat_availability(db: Session, test_show: Show, test_seats: list[Seat]) -> list[SeatAvailability]:
    """Create seat availability for all seats in a show."""
    availabilities = []
    for seat in test_seats:
        av = SeatAvailability(
            show_id=test_show.id,
            seat_id=seat.id,
            status=SeatStatus.AVAILABLE,
        )
        availabilities.append(av)
        db.add(av)
    
    db.commit()
    for av in availabilities:
        db.refresh(av)
    return availabilities


@pytest.fixture
def test_booking(db: Session, test_user: User, test_show: Show, test_seats: list[Seat]) -> Booking:
    """Create a pending booking."""
    total_amount = test_seats[0].price + test_seats[1].price
    booking = Booking(
        user_id=test_user.id,
        show_id=test_show.id,
        total_amount=total_amount,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.flush()
    
    # Add booking seats
    for seat in test_seats[:2]:
        bs = BookingSeat(booking_id=booking.id, seat_id=seat.id)
        db.add(bs)
    
    db.commit()
    db.refresh(booking)
    return booking


@pytest.fixture
def test_payment(db: Session, test_booking: Booking) -> Payment:
    """Create a pending payment."""
    payment = Payment(
        booking_id=test_booking.id,
        amount=test_booking.total_amount,
        status=PaymentStatus.PENDING,
        payment_type=PaymentType.CREDIT_CARD,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@pytest.fixture
def test_ticket(db: Session, test_booking: Booking, test_show: Show, test_movie: Movie, test_screen: Screen) -> Ticket:
    """Create a ticket for a confirmed booking."""
    ticket = Ticket(
        booking_id=test_booking.id,
        movie_name=test_movie.name,
        screen_name=test_screen.name,
        show_date=test_show.show_date.isoformat(),  # Convert date to ISO string
        show_time="14:00",  # String format
        seat_details="A1 (SILVER), A2 (SILVER)",
        total_amount=test_booking.total_amount,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
