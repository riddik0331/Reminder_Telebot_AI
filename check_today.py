import sqlite3
from datetime import datetime, timedelta
import pytz

tz = pytz.timezone("Europe/Kyiv")
now = datetime.now(tz)
today_md = now.strftime("%m-%d")
tomorrow = now + timedelta(days=1)
tomorrow_md = tomorrow.strftime("%m-%d")

print(f"Today: {today_md}")
print(f"Tomorrow: {tomorrow_md}")

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

# Check today
cur.execute(
    'SELECT id, event_date, event_name FROM events WHERE user_id=1438974394 AND STRFTIME("%m-%d", event_date) = ?',
    (today_md,),
)
print(f"\nToday events ({today_md}):")
for row in cur.fetchall():
    print(row)

# Check tomorrow
cur.execute(
    'SELECT id, event_date, event_name FROM events WHERE user_id=1438974394 AND STRFTIME("%m-%d", event_date) = ?',
    (tomorrow_md,),
)
print(f"\nTomorrow events ({tomorrow_md}):")
for row in cur.fetchall():
    print(row)
