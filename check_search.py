import sqlite3

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

search = "натусик"
search_lower = search.lower()

# Ищем события содержащие "натусик"
cur.execute("""
    SELECT id, event_date, event_name 
    FROM events 
    WHERE user_id = 1438974394 AND is_active = 1
""")
events = cur.fetchall()

found = []
for e in events:
    name_lower = e[2].lower()
    # Проверяем совпадение
    if f" {search_lower} " in f" {name_lower} ":
        found.append(("exact", e))
    elif name_lower.startswith(f"{search_lower} "):
        found.append(("start", e))
    elif any(w.startswith(search_lower) for w in name_lower.split()):
        found.append(("partial", e))

print(f"Найдено событий: {len(found)}")
for match_type, event in found[:20]:
    print(f"[{match_type}] {event}")
