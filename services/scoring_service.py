"""Scoring service for managing points and leaderboard."""
import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import PointsPerRace, User, get_db_sessionmaker


def _get_user_total_points_sync(user_id: int) -> int:
    """Synchronous helper to get user total points."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        result = session.query(func.sum(PointsPerRace.points)).filter(
            PointsPerRace.user_id == user_id
        ).scalar()
        return int(result) if result else 0
    finally:
        session.close()


def _get_leaderboard_sync(limit: Optional[int] = None) -> List[Dict]:
    """Synchronous helper to get leaderboard."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        # Get all users with their total points
        query = (
            session.query(
                User.id,
                User.telegram_id,
                User.username,
                User.full_name,
                func.coalesce(func.sum(PointsPerRace.points), 0).label('total_points')
            )
            .outerjoin(PointsPerRace, User.id == PointsPerRace.user_id)
            .group_by(User.id, User.telegram_id, User.username, User.full_name)
            .order_by(func.coalesce(func.sum(PointsPerRace.points), 0).desc())
        )
        
        if limit:
            query = query.limit(limit)
        
        results = query.all()
        
        leaderboard = []
        for rank, (user_id, telegram_id, username, full_name, total_points) in enumerate(results, 1):
            leaderboard.append({
                'rank': rank,
                'user_id': user_id,
                'telegram_id': telegram_id,
                'username': username,
                'full_name': full_name or username or f"User {telegram_id}",
                'total_points': int(total_points) if total_points else 0
            })
        
        return leaderboard
    finally:
        session.close()


def _get_user_points_per_race_sync(user_id: int) -> List[Dict]:
    """Synchronous helper to get user points per race."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        from database import Race
        results = (
            session.query(
                PointsPerRace.race_id,
                PointsPerRace.points,
                Race.name,
                Race.date
            )
            .join(Race, PointsPerRace.race_id == Race.id)
            .filter(PointsPerRace.user_id == user_id)
            .order_by(Race.date.desc())
            .all()
        )
        
        return [
            {
                'race_id': race_id,
                'points': points,
                'race_name': race_name,
                'race_date': race_date
            }
            for race_id, points, race_name, race_date in results
        ]
    finally:
        session.close()


def _get_user_bets_count_sync(user_id: int) -> int:
    """Synchronous helper to get user bets count."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    try:
        from database import Bet
        return session.query(Bet).filter(Bet.user_id == user_id).count()
    finally:
        session.close()


async def get_user_total_points(user_id: int) -> int:
    """Get user total points."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_total_points_sync, user_id)


async def get_leaderboard(limit: Optional[int] = None) -> List[Dict]:
    """Get leaderboard."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_leaderboard_sync, limit)


async def get_user_points_per_race(user_id: int) -> List[Dict]:
    """Get user points per race."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_points_per_race_sync, user_id)


async def get_user_bets_count(user_id: int) -> int:
    """Get user bets count."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_bets_count_sync, user_id)

