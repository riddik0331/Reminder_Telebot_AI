"""Database module with unified events table and connection pooling."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Any, Optional
from datetime import datetime, timedelta

import pytz

# Base directory for database path
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "app" / "my_db.sql"

# Timezone
TIMEZONE = pytz.timezone("Europe/Kyiv")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, Any, Any]:
    """
    Context manager for database connections.

    Usage:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(...)
    """
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> bool:
    """
    Initialize main database with unified events table.
    Creates all necessary tables if they don't exist.
    """
    create_tables_sql = """
    -- Main events table (unified for all users)
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_date DATE NOT NULL,
        event_name TEXT NOT NULL,
        category TEXT DEFAULT 'other',
        local_id INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        reminder_days TEXT DEFAULT '1,3,7',
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_admin INTEGER DEFAULT 0
    );
    
    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
    CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
    CREATE INDEX IF NOT EXISTS idx_events_user_date ON events(user_id, event_date);
    """

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.executescript(create_tables_sql)
            conn.commit()

        # Migrate old tables if exist
        migrate_old_tables()
        return True
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        return False


def migrate_old_tables() -> None:
    """
    Migrate data from old user-specific tables to new unified structure.
    This ensures backward compatibility.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            # Migrate old user tables
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'user_%'"
            )
            old_tables = [row[0] for row in cur.fetchall()]

            for table_name in old_tables:
                try:
                    user_id = int(table_name.replace("user_", ""))
                except ValueError:
                    continue

                cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if cur.fetchone():
                    continue

                try:
                    cur.execute(f"SELECT event_date, event_name FROM {table_name}")
                    events = cur.fetchall()

                    cur.execute(
                        "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
                    )

                    for event_date, event_name in events:
                        cur.execute(
                            "INSERT INTO events (user_id, event_date, event_name) VALUES (?, ?, ?)",
                            (user_id, event_date, event_name),
                        )
                except sqlite3.Error:
                    continue

            # Migrate category column if not exists
            cur.execute("PRAGMA table_info(events)")
            columns = [col[1] for col in cur.fetchall()]
            if "category" not in columns:
                cur.execute(
                    "ALTER TABLE events ADD COLUMN category TEXT DEFAULT 'other'"
                )
                conn.commit()

            # Migrate local_id column and calculate values
            cur.execute("PRAGMA table_info(events)")
            columns = [col[1] for col in cur.fetchall()]
            if "local_id" not in columns:
                cur.execute("ALTER TABLE events ADD COLUMN local_id INTEGER DEFAULT 0")
                conn.commit()
                # Calculate local_id for each user
                cur.execute("SELECT DISTINCT user_id FROM events")
                for (uid,) in cur.fetchall():
                    cur.execute(
                        "SELECT id FROM events WHERE user_id = ? ORDER BY id", (uid,)
                    )
                    for idx, (event_id,) in enumerate(cur.fetchall(), start=1):
                        cur.execute(
                            "UPDATE events SET local_id = ? WHERE id = ?",
                            (idx, event_id),
                        )
                conn.commit()

    except sqlite3.Error as e:
        print(f"Migration error: {e}")


async def add_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> bool:
    """Add or update user in database."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name, last_activity)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, users.username),
                    first_name = COALESCE(excluded.first_name, users.first_name),
                    last_name = COALESCE(excluded.last_name, users.last_name),
                    last_activity = CURRENT_TIMESTAMP
            """,
                (user_id, username, first_name, last_name),
            )
            conn.commit()
        return True
    except sqlite3.Error:
        return False


async def user_exists(user_id: int) -> bool:
    """Check if user exists in database."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return cur.fetchone() is not None
    except sqlite3.Error:
        return False


async def add_event(
    user_id: int,
    event_date: str,
    event_name: str,
    category: str = "other",
    reminder_days: str = "1,3,7",
) -> int | bool:
    """
    Add new event for user.

    Args:
        user_id: User ID
        event_date: Event date in YYYY-MM-DD format
        event_name: Name of the event
        category: Event category (birthday, holiday, deadline, meeting, reminder, anniversary, other)
        reminder_days: Comma-separated list of reminder days

    Returns: tuple(global_id, local_id) on success, False on error.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            # Calculate next local_id for this user
            cur.execute(
                "SELECT COALESCE(MAX(local_id), 0) FROM events WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            next_local_id = cur.fetchone()[0] + 1

            cur.execute(
                """
                INSERT INTO events (user_id, event_date, event_name, category, local_id, reminder_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    event_date,
                    event_name,
                    category,
                    next_local_id,
                    reminder_days,
                ),
            )
            conn.commit()
            global_id = cur.lastrowid
            return (global_id, next_local_id)
    except sqlite3.Error:
        return False


async def get_events(user_id: int, limit: int = 1000) -> list:
    """Get all events for user sorted by date."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_date, event_name, reminder_days, category, local_id
                FROM events
                WHERE user_id = ? AND is_active = 1
                ORDER BY event_date
                LIMIT ?
            """,
                (user_id, limit),
            )
            return cur.fetchall()
    except sqlite3.Error:
        return []


async def get_event_by_id(event_id: int, user_id: int) -> Optional[dict]:
    """Get single event by global ID (internal use)."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_date, event_name, reminder_days, category, local_id
                FROM events
                WHERE id = ? AND user_id = ?
            """,
                (event_id, user_id),
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "event_date": row[1],
                    "event_name": row[2],
                    "reminder_days": row[3],
                    "category": row[4] if len(row) > 4 else "other",
                    "local_id": row[5] if len(row) > 5 else 0,
                }
    except sqlite3.Error:
        pass
    return None


async def get_event_by_local_id(local_id: int, user_id: int) -> Optional[dict]:
    """Get single event by local ID (user-facing)."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_date, event_name, reminder_days, category, local_id
                FROM events
                WHERE local_id = ? AND user_id = ? AND is_active = 1
            """,
                (local_id, user_id),
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "event_date": row[1],
                    "event_name": row[2],
                    "reminder_days": row[3],
                    "category": row[4] if len(row) > 4 else "other",
                    "local_id": row[5],
                }
    except sqlite3.Error:
        pass
    return None


async def delete_event(user_id: int, event_id: int) -> int:
    """
    Delete event by local ID (soft delete).

    Args:
        user_id: User ID
        event_id: Local event ID (as shown to user)

    Returns number of rows affected.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE events 
                SET is_active = 0 
                WHERE local_id = ? AND user_id = ? AND is_active = 1
            """,
                (event_id, user_id),
            )
            conn.commit()
            return cur.rowcount
    except sqlite3.Error:
        return 0


async def delete_events(user_id: int, event_ids: list[int]) -> tuple[int, list, list]:
    """
    Delete multiple events by local IDs (soft delete).

    Args:
        user_id: User ID
        event_ids: List of local event IDs to delete

    Returns:
        Tuple of (deleted_count, deleted_ids, not_found_ids)
    """
    if not event_ids:
        return 0, [], []

    try:
        deleted_count = 0
        deleted_ids = []
        not_found_ids = []

        with get_connection() as conn:
            cur = conn.cursor()

            for event_id in event_ids:
                cur.execute(
                    """
                    UPDATE events 
                    SET is_active = 0 
                    WHERE local_id = ? AND user_id = ? AND is_active = 1
                """,
                    (event_id, user_id),
                )
                if cur.rowcount > 0:
                    deleted_count += cur.rowcount
                    deleted_ids.append(event_id)
                else:
                    not_found_ids.append(event_id)

            conn.commit()

        return deleted_count, deleted_ids, not_found_ids
    except sqlite3.Error:
        return 0, [], []


async def get_events_by_local_ids(user_id: int, event_ids: list[int]) -> list:
    """
    Get events by local IDs.

    Args:
        user_id: User ID
        event_ids: List of local event IDs

    Returns:
        List of event dicts
    """
    if not event_ids:
        return []

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" * len(event_ids))
            cur.execute(
                f"""
                SELECT id, event_date, event_name, reminder_days, category, local_id
                FROM events
                WHERE local_id IN ({placeholders}) AND user_id = ? AND is_active = 1
            """,
                (*event_ids, user_id),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "event_date": row[1],
                    "event_name": row[2],
                    "reminder_days": row[3],
                    "category": row[4] if len(row) > 4 else "other",
                    "local_id": row[5],
                }
                for row in rows
            ]
    except sqlite3.Error:
        return []


async def delete_user_events(user_id: int) -> bool:
    """Delete all events for user (soft delete)."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE events SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
        return True
    except sqlite3.Error:
        return False


async def get_events_for_date(user_id: int, target_date: str) -> list:
    """Get events for specific date."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_date, event_name 
                FROM events
                WHERE user_id = ? AND event_date = ? AND is_active = 1
            """,
                (user_id, target_date),
            )
            return cur.fetchall()
    except sqlite3.Error:
        return []


async def get_events_for_period(user_id: int, period: str) -> tuple[list, str]:
    """
    Get events for specified period.

    Args:
        user_id: User ID
        period: One of 'today', 'tomorrow', 'this_month', 'next_month'

    Returns:
        Tuple of (events_list, period_name_ukrainian)
    """
    now = datetime.now(TIMEZONE)
    today = now.date()
    current_month = today.month

    # Calculate month ranges
    if current_month == 12:
        next_month = 1
    else:
        next_month = current_month + 1

    period_queries = {
        "today": (
            f"{today.strftime('%m')}-{today.strftime('%d')}",
            "Події на сьогодні",
            "mm-dd",  # format type
        ),
        "tomorrow": (
            f"{(today + timedelta(days=1)).strftime('%m')}-{(today + timedelta(days=1)).strftime('%d')}",
            "Події на завтра",
            "mm-dd",
        ),
        "this_month": (
            today.strftime("%m"),
            "Події на поточний місяць",
            "mm",  # format type
        ),
        "next_month": (
            f"{next_month:02d}",
            "Події на наступний місяць",
            "mm",
        ),
    }

    if period not in period_queries:
        return [], ""

    start_date, period_name, date_format = period_queries[period]

    try:
        with get_connection() as conn:
            cur = conn.cursor()

            if date_format == "mm-dd":
                # For today/tomorrow - match exact day
                cur.execute(
                    """
                    SELECT id, event_date, event_name,
                        CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - 
                             CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' as anniversary,
                        local_id, category
                    FROM events
                    WHERE user_id = ? AND STRFTIME('%m-%d', event_date) = ? AND is_active = 1
                    ORDER BY STRFTIME('%m-%d', event_date), event_date
                """,
                    (user_id, start_date),
                )
            else:
                # For months - match month only
                cur.execute(
                    """
                    SELECT id, event_date, event_name,
                        CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - 
                             CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' as anniversary,
                        local_id, category
                    FROM events
                    WHERE user_id = ? AND STRFTIME('%m', event_date) = ? AND is_active = 1
                    ORDER BY STRFTIME('%m-%d', event_date), event_date
                """,
                    (user_id, start_date),
                )
            return cur.fetchall(), period_name
    except sqlite3.Error as e:
        print(f"Error getting events for period: {e}")
        return [], ""


async def get_events_by_category_for_month(user_id: int, year: int, month: int) -> dict:
    """
    Get events for a specific month grouped by category.

    Args:
        user_id: User ID
        year: Year (e.g., 2026)
        month: Month (1-12)

    Returns:
        Dict with category as key and list of (date, name, local_id) as value
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            month_str = f"{month:02d}"

            cur.execute(
                """
                SELECT event_date, event_name, local_id, category
                FROM events
                WHERE user_id = ? 
                    AND STRFTIME('%m', event_date) = ?
                    AND is_active = 1
                ORDER BY event_date
                """,
                (user_id, month_str),
            )

            events = cur.fetchall()

            # Group by category
            by_category = {}
            for event_date, event_name, local_id, category in events:
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append((event_date, event_name, local_id))

            return by_category

    except sqlite3.Error as e:
        print(f"Error getting events by category: {e}")
        return {}


async def get_events_for_today(user_id: int) -> str:
    """Get events for today formatted as text (for daily reminder)."""
    now = datetime.now(TIMEZONE)
    today_md = now.strftime("%m-%d")

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            # Match by month-day, not full date
            cur.execute(
                """
                SELECT id, event_date, event_name,
                    CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - 
                         CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' as anniversary
                FROM events
                WHERE user_id = ? AND STRFTIME('%m-%d', event_date) = ? AND is_active = 1
                ORDER BY event_date
            """,
                (user_id, today_md),
            )
            events = cur.fetchall()
            return "\n\n".join(
                [f"ID: {e[0]}\nДата: {e[1]}\nПодія: {e[2]}\n{e[3]}" for e in events]
            )
    except sqlite3.Error:
        return ""


async def get_events_with_reminders() -> list:
    """
    Get events that need reminder notifications.
    Returns list of (user_id, event_id, event_date, event_name, reminder_days, category)
    """
    now = datetime.now(TIMEZONE)
    today = now.date()

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_id, id, event_date, event_name, reminder_days, category
                FROM events
                WHERE is_active = 1 AND event_date >= ?
                ORDER BY event_date
            """,
                (today.strftime("%Y-%m-%d"),),
            )
            return cur.fetchall()
    except sqlite3.Error:
        return []


async def get_user_ids() -> list[int]:
    """Get all user IDs from database."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT user_id FROM users")
            return [row[0] for row in cur.fetchall()]
    except sqlite3.Error:
        return []


async def get_users_stats() -> dict[int, int]:
    """Get user statistics: {user_id: event_count}."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, COUNT(*) as event_count
                FROM events
                WHERE is_active = 1
                GROUP BY user_id
            """)
            return {row[0]: row[1] for row in cur.fetchall()}
    except sqlite3.Error:
        return {}


async def search_events(user_id: int, key_word: str) -> list:
    """Search events by keyword."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_date, event_name,
                    CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - 
                         CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' as anniversary
                FROM events
                WHERE user_id = ? AND event_name LIKE ? AND is_active = 1
                ORDER BY event_date
            """,
                (user_id, f"%{key_word}%"),
            )
            return cur.fetchall()
    except sqlite3.Error:
        return []


async def search_events_fuzzy(user_id: int, key_word: str) -> list:
    """
    Hybrid search with multiple matching strategies:
    1. Exact match (query in event_name)     → priority 100%
    2. Event starts with query              → priority 95%
    3. Word starts with query (strict)      → priority 90%
    4. Prefix fuzzy (query vs word start)   → dynamic score
       Requires: ≥3 matching chars AND ratio ≥70%

    Short queries (1-2 chars) return empty results.
    Uses ONLY fuzz.ratio (NOT partial_ratio) to avoid false positives.
    """
    from rapidfuzz import fuzz

    events = await get_events(user_id)
    if not events:
        return []

    key_word_lower = key_word.lower().strip()
    query_len = len(key_word_lower)
    results = {}

    # Constants for matching
    min_exact_len = 2
    min_prefix_len = 2
    min_fuzzy_len = 3
    prefix_fuzzy_threshold = 70  # Threshold for prefix fuzzy matching
    min_match_chars = 3  # Minimum matching characters for prefix fuzzy

    for event in events:
        event_id = event[0]
        event_name = event[2]
        event_name_lower = event_name.lower()
        words = event_name_lower.split()

        # 1. Exact match (query is substring of event name)
        if query_len >= min_exact_len and key_word_lower in event_name_lower:
            results[event_id] = (100, event, 100)
            continue

        # 2. Event name starts with query
        if query_len >= min_prefix_len and event_name_lower.startswith(key_word_lower):
            results[event_id] = (95, event, 95)
            continue

        # 3. Word starts with query (strict prefix match)
        word_prefix_found = False
        if query_len >= min_prefix_len:
            for word in words:
                if word.startswith(key_word_lower):
                    results[event_id] = (90, event, 90)
                    word_prefix_found = True
                    break

        if word_prefix_found:
            continue

        # 4. Prefix fuzzy - query is similar to start of a word
        # "нату" vs "наталью" → compares "нату" with "натал" (word start)
        if query_len >= min_fuzzy_len:
            best_score = 0

            for word in words:
                if len(word) >= min_match_chars:
                    # Compare query with first N chars of word
                    compare_len = min(query_len, len(word))
                    word_prefix = word[:compare_len]

                    # Count matching characters
                    char_match = sum(
                        1 for a, b in zip(key_word_lower, word_prefix) if a == b
                    )

                    # Calculate ratio for prefix
                    score = fuzz.ratio(key_word_lower, word_prefix)

                    # Accept if ≥3 chars match AND ratio ≥ threshold
                    if (
                        char_match >= min_match_chars
                        and score >= prefix_fuzzy_threshold
                    ):
                        if score > best_score:
                            best_score = score

            if best_score > 0:
                results[event_id] = (best_score, event, best_score)

    # Sort by priority/score descending
    sorted_results = sorted(results.values(), key=lambda x: -x[0])

    # Format results with anniversary info, category and local_id
    formatted = []
    for priority, event, score in sorted_results:
        try:
            event_year = int(event[1].split("-")[0])
            current_year = datetime.now(TIMEZONE).year
            anniversary = f"{current_year - event_year}-я годовщина"
        except:
            anniversary = ""

        # Get category from event tuple (index 4)
        category = event[4] if len(event) > 4 else "other"
        # Get local_id from event tuple (index 5)
        local_id = event[5] if len(event) > 5 else 0

        formatted.append(
            (event[0], event[1], event[2], anniversary, category, local_id)
        )

    return formatted


# Legacy compatibility functions
async def init_user_table(user_id: int) -> bool:
    """Legacy function - creates user entry in new structure."""
    return await add_user(user_id)


async def table_exists(user_id: int) -> bool:
    """Legacy function - checks if user has events."""
    return await user_exists(user_id)


def get_user_table_name(user_id: int) -> str:
    """Legacy function - returns table name for compatibility."""
    return f"user_{user_id}"


async def delete_user_table(user_id: int) -> bool:
    """Legacy function - deletes all user events."""
    return await delete_user_events(user_id)


async def check_admin_password(password: str, expected_password: str) -> bool:
    """Legacy function - checks password (consider moving to hashed)."""
    import hashlib

    return (
        hashlib.sha256(password.encode()).hexdigest()
        == hashlib.sha256(expected_password.encode()).hexdigest()
    )


# Initialize database on module load
init_database()
