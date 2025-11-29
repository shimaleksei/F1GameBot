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
            # Admins are automatically allowed, others need to be approved
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                is_admin=is_admin(telegram_id),
                is_allowed=is_admin(telegram_id),  # Admins are auto-allowed
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


def _set_user_allowed_sync(telegram_id: int, allowed: bool) -> bool:
    """Synchronous helper to set user allowed status."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        user.is_allowed = allowed
        session.commit()
        return True
    finally:
        session.close()


async def set_user_allowed(telegram_id: int, allowed: bool) -> bool:
    """Set user allowed status (whitelist)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _set_user_allowed_sync,
        telegram_id,
        allowed
    )


def _get_all_users_sync() -> list:
    """Synchronous helper to get all users."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    
    try:
        return session.query(User).order_by(User.created_at.desc()).all()
    finally:
        session.close()


async def get_all_users() -> list:
    """Get all users."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_all_users_sync)


def _get_user_by_username_sync(username: str) -> Optional[User]:
    """Synchronous helper to get user by username."""
    SessionLocal = get_db_sessionmaker()
    session = SessionLocal()
    
    try:
        # Remove @ if present
        username_clean = username.lstrip('@')
        return session.query(User).filter(User.username == username_clean).first()
    finally:
        session.close()


async def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username (with or without @)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _get_user_by_username_sync,
        username
    )

