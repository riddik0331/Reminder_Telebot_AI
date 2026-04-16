import sqlite3

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

# Get last 10 events
cur.execute(
    "SELECT id, event_date, event_name FROM events WHERE user_id=1438974394 ORDER BY id DESC LIMIT 10"
)
for row in cur.fetchall():
    print(row)

# Check 04-14 and 04-15
cur.execute(
    'SELECT COUNT(*) FROM events WHERE user_id=1438974394 AND STRFTIME("%m-%d", event_date) IN ("04-14", "04-15")'
)
print(f"\nEvents on 04-14 or 04-15: {cur.fetchone()[0]}")
