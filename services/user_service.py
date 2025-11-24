"""User service for managing users."""
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from database import User, get_db_sessionmaker
from config import is_admin


def _get_or_create_user_sync(telegram_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> User:
    """Synchronous helper for get_or_create_user."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                is_admin=is_admin(telegram_id),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        else:
            # Update existing user info
            if username and user.username != username:
                user.username = username
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            # Update admin status in case it changed in config
            user.is_admin = is_admin(telegram_id)
            session.commit()
            session.refresh(user)
        
        return user
    finally:
        session.close()


async def get_or_create_user(telegram_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> User:
    """Get existing user or create new one (F-002)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _get_or_create_user_sync,
        telegram_id,
        username,
        full_name
    )


def _get_user_by_telegram_id_sync(telegram_id: int) -> Optional[User]:
    """Synchronous helper for get_user_by_telegram_id."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    
    try:
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    finally:
        session.close()


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """Get user by Telegram ID."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _get_user_by_telegram_id_sync,
        telegram_id
    )

