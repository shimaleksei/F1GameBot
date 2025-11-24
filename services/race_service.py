"""Race service for managing races."""
import asyncio
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from database import Race, get_db_sessionmaker


def _get_all_races_sync() -> List[Race]:
    """Synchronous helper to get all races."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(Race).order_by(Race.date, Race.start_time).all()
    finally:
        session.close()


def _get_race_by_id_sync(race_id: int) -> Optional[Race]:
    """Synchronous helper to get race by ID."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(Race).filter(Race.id == race_id).first()
    finally:
        session.close()


def _create_race_sync(name: str, date: str, start_time: str, timezone: str = "UTC") -> Race:
    """Synchronous helper to create race."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        race = Race(
            name=name,
            date=date,
            start_time=start_time,
            timezone=timezone,
            status="upcoming",
            reminder_sent=False
        )
        session.add(race)
        session.commit()
        session.refresh(race)
        return race
    finally:
        session.close()


def _update_race_sync(race_id: int, name: Optional[str] = None, date: Optional[str] = None,
                     start_time: Optional[str] = None, timezone: Optional[str] = None,
                     status: Optional[str] = None) -> Optional[Race]:
    """Synchronous helper to update race."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        race = session.query(Race).filter(Race.id == race_id).first()
        if not race:
            return None
        
        if name is not None:
            race.name = name
        if date is not None:
            race.date = date
        if start_time is not None:
            race.start_time = start_time
        if timezone is not None:
            race.timezone = timezone
        if status is not None:
            race.status = status
        
        session.commit()
        session.refresh(race)
        return race
    finally:
        session.close()


def _delete_race_sync(race_id: int) -> bool:
    """Synchronous helper to delete race."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        race = session.query(Race).filter(Race.id == race_id).first()
        if not race:
            return False
        session.delete(race)
        session.commit()
        return True
    finally:
        session.close()


def _get_upcoming_races_sync() -> List[Race]:
    """Synchronous helper to get upcoming races."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(Race).filter(Race.status == "upcoming").order_by(Race.date, Race.start_time).all()
    finally:
        session.close()


async def get_all_races() -> List[Race]:
    """Get all races."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_all_races_sync)


async def get_race_by_id(race_id: int) -> Optional[Race]:
    """Get race by ID."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_race_by_id_sync, race_id)


async def create_race(name: str, date: str, start_time: str, timezone: str = "UTC") -> Race:
    """Create new race."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _create_race_sync, name, date, start_time, timezone)


async def update_race(race_id: int, name: Optional[str] = None, date: Optional[str] = None,
                     start_time: Optional[str] = None, timezone: Optional[str] = None,
                     status: Optional[str] = None) -> Optional[Race]:
    """Update race."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _update_race_sync, race_id, name, date, start_time, timezone, status
    )


async def delete_race(race_id: int) -> bool:
    """Delete race."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _delete_race_sync, race_id)


async def get_upcoming_races() -> List[Race]:
    """Get upcoming races."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_upcoming_races_sync)

