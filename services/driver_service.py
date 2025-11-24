"""Driver service for managing drivers."""
import asyncio
from typing import List, Optional
from sqlalchemy.orm import Session
from database import Driver, get_db_sessionmaker


def _get_all_drivers_sync(active_only: bool = True) -> List[Driver]:
    """Synchronous helper to get all drivers."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        query = session.query(Driver)
        if active_only:
            query = query.filter(Driver.is_active == True)
        return query.order_by(Driver.code).all()
    finally:
        session.close()


def _get_driver_by_code_sync(code: str) -> Optional[Driver]:
    """Synchronous helper to get driver by code."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(Driver).filter(Driver.code == code).first()
    finally:
        session.close()


async def get_all_drivers(active_only: bool = True) -> List[Driver]:
    """Get all drivers."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_all_drivers_sync, active_only)


async def get_driver_by_code(code: str) -> Optional[Driver]:
    """Get driver by code."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_driver_by_code_sync, code)

