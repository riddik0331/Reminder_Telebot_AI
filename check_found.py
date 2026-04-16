import sqlite3
import sys

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

ids = [11, 42, 117, 24, 104, 55, 64]

with open("found_events.txt", "w", encoding="utf-8") as f:
    f.write("События найденные ботом по запросу 'Любимая':\n")
    f.write("=" * 60 + "\n\n")

    for id in ids:
        cur.execute("SELECT id, event_date, event_name FROM events WHERE id=?", (id,))
        row = cur.fetchone()
        if row:
            f.write(f"ID {row[0]}: {row[2]} ({row[1][:10]})\n")

print("Done")
