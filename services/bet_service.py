"""Bet service for managing bets."""
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import Bet, get_db_sessionmaker
from config import BET_CLOSING_OFFSET, DEFAULT_TIMEZONE
import pytz


def _get_bet_sync(user_id: int, race_id: int) -> Optional[Bet]:
    """Synchronous helper to get bet by user and race."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(Bet).filter(
            Bet.user_id == user_id,
            Bet.race_id == race_id
        ).first()
    finally:
        session.close()


def _create_bet_sync(user_id: int, race_id: int, driver_1st: str, driver_2nd: str, driver_3rd: str) -> Bet:
    """Synchronous helper to create bet."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        # Check if bet already exists
        existing_bet = session.query(Bet).filter(
            Bet.user_id == user_id,
            Bet.race_id == race_id
        ).first()
        
        if existing_bet:
            # Update existing bet
            existing_bet.driver_1st = driver_1st
            existing_bet.driver_2nd = driver_2nd
            existing_bet.driver_3rd = driver_3rd
            existing_bet.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(existing_bet)
            return existing_bet
        else:
            # Create new bet
            bet = Bet(
                user_id=user_id,
                race_id=race_id,
                driver_1st=driver_1st,
                driver_2nd=driver_2nd,
                driver_3rd=driver_3rd
            )
            session.add(bet)
            session.commit()
            session.refresh(bet)
            return bet
    finally:
        session.close()


def _get_user_bets_sync(user_id: int) -> List[Bet]:
    """Synchronous helper to get all user bets."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(Bet).filter(Bet.user_id == user_id).order_by(Bet.created_at.desc()).all()
    finally:
        session.close()


def _delete_bet_sync(user_id: int, race_id: int) -> bool:
    """Synchronous helper to delete bet."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        bet = session.query(Bet).filter(
            Bet.user_id == user_id,
            Bet.race_id == race_id
        ).first()
        if not bet:
            return False
        session.delete(bet)
        session.commit()
        return True
    finally:
        session.close()


async def get_bet(user_id: int, race_id: int) -> Optional[Bet]:
    """Get bet by user and race."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_bet_sync, user_id, race_id)


async def create_or_update_bet(user_id: int, race_id: int, driver_1st: str, driver_2nd: str, driver_3rd: str) -> Bet:
    """Create or update bet."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _create_bet_sync, user_id, race_id, driver_1st, driver_2nd, driver_3rd
    )


async def get_user_bets(user_id: int) -> List[Bet]:
    """Get all user bets."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_bets_sync, user_id)


async def delete_bet(user_id: int, race_id: int) -> bool:
    """Delete bet."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _delete_bet_sync, user_id, race_id)


def is_betting_open(race_date: str, race_time: str, race_timezone: str) -> bool:
    """Check if betting is still open for a race."""
    try:
        # Parse race date and time
        race_datetime_str = f"{race_date} {race_time}"
        race_dt = datetime.strptime(race_datetime_str, "%Y-%m-%d %H:%M")
        
        # Convert to timezone
        tz = pytz.timezone(race_timezone)
        race_dt = tz.localize(race_dt)
        
        # Get current time in race timezone
        now = datetime.now(tz)
        
        # Calculate race start time minus closing offset
        race_start = race_dt
        betting_closes_at = race_start - timedelta(minutes=BET_CLOSING_OFFSET)
        
        # Check if current time is before betting closes
        return now < betting_closes_at
    except Exception:
        # If parsing fails, assume betting is closed
        return False

