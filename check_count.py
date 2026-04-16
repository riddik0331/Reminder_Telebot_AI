import sqlite3

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM events WHERE user_id = 1438974394 AND is_active = 1")
total = cur.fetchone()[0]
print(f"Всего событий: {total}")

# Проверяем поиск "натусик"
search = "натусик"
found = 0
found_names = []

cur.execute(
    "SELECT event_name FROM events WHERE user_id = 1438974394 AND is_active = 1"
)
for (name,) in cur.fetchall():
    name_lower = name.lower()
    # Слов от 3 букв - совпадение от начала
    for kw in search.split():
        for w in name_lower.split():
            if w.startswith(kw[:3]):
                found += 1
                found_names.append(name[:50])
                break
        else:
            continue
        break

print(f"Совпадений: {found}")
print("Первые 5:", found_names[:5])
