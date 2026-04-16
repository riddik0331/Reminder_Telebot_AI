import sqlite3

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

# Check tomorrow (04-15)
cur.execute(
    'SELECT id, event_date FROM events WHERE user_id=1438974394 AND STRFTIME("%m-%d", event_date) = "04-15"'
)
print("04-15 events:", cur.fetchall())

# Check what the query returns for tomorrow
from datetime import datetime, timedelta
import pytz

tz = pytz.timezone("Europe/Kyiv")
now = datetime.now(tz)
tomorrow = now + timedelta(days=1)
tomorrow_md = tomorrow.strftime("%m-%d")
print(f"Tomorrow format: {tomorrow_md}")
