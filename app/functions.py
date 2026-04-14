"""Helper functions for the Telegram Reminder Bot."""

from datetime import datetime
import pandas as pd
from pathlib import Path


# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


async def validate_date(date_str: str) -> bool:
    """
    Validate date format YYYY-MM-DD.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


async def check_admin_password(password: str, expected_password: str) -> bool:
    """
    Check admin password.
    
    Args:
        password: Password to check
        expected_password: Expected password from config
        
    Returns:
        True if passwords match
    """
    return password == expected_password


async def export_to_excel(users_db: dict[int, int]) -> str:
    """
    Export user statistics to Excel file.
    
    Args:
        users_db: Dictionary {user_id: event_count}
        
    Returns:
        Path to exported file
    """
    user_data = [
        {
            "ID користувача": user_id,
            "Кількість подій": count
        }
        for user_id, count in users_db.items()
    ]
    
    df = pd.DataFrame(user_data)
    
    file_path = BASE_DIR / "users_data.xlsx"
    df.to_excel(file_path, index=False, engine='openpyxl')
    
    return str(file_path)
