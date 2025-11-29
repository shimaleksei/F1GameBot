"""Configuration module for F1 Game Bot."""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin user IDs (comma-separated string converted to list of integers)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [
    int(admin_id.strip())
    for admin_id in ADMIN_IDS_STR.split(",")
    if admin_id.strip().isdigit()
]

# Database configuration
# Use absolute path if provided, otherwise use relative path in current directory
# IMPORTANT: On servers where working directory may be cleared, use absolute path via DATABASE_PATH env var
DATABASE_PATH = os.getenv("DATABASE_PATH", "f1bot.db")
# Convert to absolute path if relative (helps with persistence)
if not os.path.isabs(DATABASE_PATH):
    DATABASE_PATH = os.path.abspath(DATABASE_PATH)

# Default timezone (supports both TIMEZONE and DEFAULT_TIMEZONE for compatibility)
DEFAULT_TIMEZONE = os.getenv("TIMEZONE") or os.getenv("DEFAULT_TIMEZONE", "UTC")

# Bet closing offset in minutes before race start
BET_CLOSING_OFFSET = int(os.getenv("BET_CLOSING_OFFSET", "5"))

# Reminder time in hours before race start
REMINDER_HOURS_BEFORE = 2


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMIN_IDS


def validate_config() -> bool:
    """Validate that required configuration is present."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment variables")
    if not ADMIN_IDS:
        raise ValueError("ADMIN_IDS is not set or invalid")
    return True

