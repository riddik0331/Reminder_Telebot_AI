import os
from pathlib import Path
from dotenv import load_dotenv
import pytz
from functools import lru_cache

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Bot configuration
TELEBOT_TOKEN = os.getenv("TELEBOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1111")

# Groq AI Configuration (optional)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Timezone configuration (Kyiv time)
TIMEZONE = pytz.timezone("Europe/Kyiv")

# Reminder settings
DEFAULT_REMINDER_DAYS = [1, 3, 7]  # Days before event to send reminder

# Validation
if not TELEBOT_TOKEN:
    raise ValueError(
        "TELEBOT_TOKEN not found in environment variables. Please set it in .env file"
    )


@lru_cache()
def get_admin_password_hash() -> str:
    """Get hashed admin password for secure comparison."""
    import hashlib

    return hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
