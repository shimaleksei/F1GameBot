"""Result service for managing race results and scoring."""
import asyncio
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from database import RaceResult, Bet, PointsPerRace, get_db_sessionmaker


def _get_result_by_race_id_sync(race_id: int) -> Optional[RaceResult]:
    """Synchronous helper to get result by race ID."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        return session.query(RaceResult).filter(RaceResult.race_id == race_id).first()
    finally:
        session.close()


def _create_or_update_result_sync(race_id: int, driver_1st: str, driver_2nd: str, driver_3rd: str) -> RaceResult:
    """Synchronous helper to create or update result."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        existing_result = session.query(RaceResult).filter(RaceResult.race_id == race_id).first()
        
        if existing_result:
            # Update existing result
            existing_result.driver_1st = driver_1st
            existing_result.driver_2nd = driver_2nd
            existing_result.driver_3rd = driver_3rd
            existing_result.saved_at = datetime.utcnow()
            session.commit()
            session.refresh(existing_result)
            return existing_result
        else:
            # Create new result
            result = RaceResult(
                race_id=race_id,
                driver_1st=driver_1st,
                driver_2nd=driver_2nd,
                driver_3rd=driver_3rd
            )
            session.add(result)
            session.commit()
            session.refresh(result)
            return result
    finally:
        session.close()


def _calculate_points_for_bet(bet: Bet, result: RaceResult) -> int:
    """Calculate points for a single bet based on scoring rules (F-007)."""
    points = 0
    
    # Check each position
    # 1st place
    if bet.driver_1st == result.driver_1st:
        points += 3  # Exact position
    elif bet.driver_1st in [result.driver_1st, result.driver_2nd, result.driver_3rd]:
        points += 1  # In top 3 but wrong position
    
    # 2nd place
    if bet.driver_2nd == result.driver_2nd:
        points += 3  # Exact position
    elif bet.driver_2nd in [result.driver_1st, result.driver_2nd, result.driver_3rd]:
        points += 1  # In top 3 but wrong position
    
    # 3rd place
    if bet.driver_3rd == result.driver_3rd:
        points += 3  # Exact position
    elif bet.driver_3rd in [result.driver_1st, result.driver_2nd, result.driver_3rd]:
        points += 1  # In top 3 but wrong position
    
    return points


def _calculate_and_save_points_sync(race_id: int, result: RaceResult) -> List[dict]:
    """Synchronous helper to calculate and save points for all bets."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        # Get all bets for this race
        bets = session.query(Bet).filter(Bet.race_id == race_id).all()
        
        points_summary = []
        
        for bet in bets:
            # Calculate points
            points = _calculate_points_for_bet(bet, result)
            
            # Check if points already exist
            existing_points = session.query(PointsPerRace).filter(
                PointsPerRace.user_id == bet.user_id,
                PointsPerRace.race_id == race_id
            ).first()
            
            if existing_points:
                # Update existing points
                existing_points.points = points
            else:
                # Create new points record
                points_record = PointsPerRace(
                    user_id=bet.user_id,
                    race_id=race_id,
                    points=points
                )
                session.add(points_record)
            
            # Get user for summary
            from database import User
            user = session.query(User).filter(User.id == bet.user_id).first()
            points_summary.append({
                'user_id': bet.user_id,
                'user_name': user.full_name if user and user.full_name else (user.username if user else f"User {bet.user_id}"),
                'points': points
            })
        
        session.commit()
        return points_summary
    finally:
        session.close()


def _get_races_without_results_sync() -> List:
    """Synchronous helper to get races without results."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        from database import Race
        # Get races that don't have results yet
        races_with_results = session.query(RaceResult.race_id).subquery()
        races = session.query(Race).filter(
            ~Race.id.in_(session.query(races_with_results))
        ).order_by(Race.date, Race.start_time).all()
        return races
    finally:
        session.close()


async def get_result_by_race_id(race_id: int) -> Optional[RaceResult]:
    """Get result by race ID."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_result_by_race_id_sync, race_id)


async def create_or_update_result(race_id: int, driver_1st: str, driver_2nd: str, driver_3rd: str) -> RaceResult:
    """Create or update race result."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _create_or_update_result_sync, race_id, driver_1st, driver_2nd, driver_3rd
    )


async def calculate_and_save_points(race_id: int, result: RaceResult) -> List[dict]:
    """Calculate and save points for all bets."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _calculate_and_save_points_sync, race_id, result)


async def get_races_without_results() -> List:
    """Get races without results."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_races_without_results_sync)

