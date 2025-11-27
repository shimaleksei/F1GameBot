"""Database setup and models for F1 Game Bot."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, Session
from aiosqlite import connect as aiosqlite_connect
import aiosqlite

from config import DATABASE_PATH

Base = declarative_base()


# Models
class User(Base):
    """User model (D-001)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    wants_reminders = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    bets = relationship("Bet", back_populates="user", cascade="all, delete-orphan")
    points = relationship("PointsPerRace", back_populates="user", cascade="all, delete-orphan")


class Driver(Base):
    """Driver model (D-002)."""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # e.g., VER, LEC, HAM
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Race(Base):
    """Race model (D-003)."""
    __tablename__ = "races"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    start_time = Column(String(5), nullable=False)  # HH:MM
    timezone = Column(String(50), nullable=False, default="UTC")
    status = Column(String(20), default="upcoming", nullable=False)  # upcoming / finished
    reminder_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    bets = relationship("Bet", back_populates="race", cascade="all, delete-orphan")
    result = relationship("RaceResult", back_populates="race", uselist=False, cascade="all, delete-orphan")


class Bet(Base):
    """Bet model (D-004)."""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False, index=True)
    driver_1st = Column(String(10), nullable=False)  # Driver code
    driver_2nd = Column(String(10), nullable=False)  # Driver code
    driver_3rd = Column(String(10), nullable=False)  # Driver code
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bets")
    race = relationship("Race", back_populates="bets")


class RaceResult(Base):
    """Race result model (D-005)."""
    __tablename__ = "race_results"

    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.id"), unique=True, nullable=False, index=True)
    driver_1st = Column(String(10), nullable=False)  # Driver code
    driver_2nd = Column(String(10), nullable=False)  # Driver code
    driver_3rd = Column(String(10), nullable=False)  # Driver code
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    race = relationship("Race", back_populates="result")


class PointsPerRace(Base):
    """Points per race model (D-006)."""
    __tablename__ = "points_per_race"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False, index=True)
    points = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="points")


# Database engine and session
# Note: aiosqlite doesn't work directly with SQLAlchemy async, so we'll use sync engine
# but wrap operations in async functions
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)


def _init_db_sync():
    """Synchronous helper for init_db."""
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Seed initial drivers if table is empty
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        driver_count = session.query(Driver).count()
        if driver_count == 0:
            # Add current F1 drivers (2025 season)
            drivers = [
                Driver(code="VER", full_name="Max Verstappen", is_active=True),
                Driver(code="LAW", full_name="Liam Lawson", is_active=True),
                Driver(code="LEC", full_name="Charles Leclerc", is_active=True),
                Driver(code="HAM", full_name="Lewis Hamilton", is_active=True),
                Driver(code="RUS", full_name="George Russell", is_active=True),
                Driver(code="ANT", full_name="Andrea Kimi Antonelli", is_active=True),
                Driver(code="NOR", full_name="Lando Norris", is_active=True),
                Driver(code="PIA", full_name="Oscar Piastri", is_active=True),
                Driver(code="ALO", full_name="Fernando Alonso", is_active=True),
                Driver(code="STR", full_name="Lance Stroll", is_active=True),
                Driver(code="GAS", full_name="Pierre Gasly", is_active=True),
                Driver(code="DOO", full_name="Jack Doohan", is_active=True),
                Driver(code="ALB", full_name="Alex Albon", is_active=True),
                Driver(code="SAI", full_name="Carlos Sainz Jr.", is_active=True),
                Driver(code="OCO", full_name="Esteban Ocon", is_active=True),
                Driver(code="BEA", full_name="Oliver Bearman", is_active=True),
                Driver(code="TSU", full_name="Yuki Tsunoda", is_active=True),
                Driver(code="HAD", full_name="Isack Hadjar", is_active=True),
                Driver(code="HUL", full_name="Nico Hülkenberg", is_active=True),
                Driver(code="BOR", full_name="Gabriel Bortoleto", is_active=True),
            ]
            session.add_all(drivers)
            session.commit()
            print(f"Seeded {len(drivers)} drivers")
    finally:
        session.close()


async def init_db():
    """Initialize database and create tables."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _init_db_sync)


def get_db_sessionmaker():
    """Get database sessionmaker."""
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(bind=engine)

