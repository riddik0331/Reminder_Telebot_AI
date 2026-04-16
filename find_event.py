import sqlite3

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

# Ищем события на 05.07
cur.execute(
    'SELECT id, event_date, event_name FROM events WHERE user_id=1438974394 AND STRFTIME("%m-%d", event_date)="07-05"'
)
print("События на 05.07:")
for row in cur.fetchall():
    print(row)

# Ищем все с "Натусик"
cur.execute(
    'SELECT id, event_date, event_name FROM events WHERE user_id=1438974394 AND event_name LIKE "%Натусик%"'
)
print("\nС 'Натусик':")
for row in cur.fetchall():
    print(row)
