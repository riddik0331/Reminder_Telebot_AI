import sqlite3
from datetime import datetime

conn = sqlite3.connect("app/my_db.sql")
cur = conn.cursor()

# Получаем все события
cur.execute("""
    SELECT id, event_date, event_name 
    FROM events 
    WHERE user_id = 1438974394 AND is_active = 1
    ORDER BY STRFTIME("%m-%d", event_date), event_date
""")
events = cur.fetchall()

# Формируем текст
lines = []
lines.append(f"Все события пользователя (всего: {len(events)})")
lines.append(f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
lines.append("Сортировка: Январь → Декабрь")
lines.append("=" * 60)
lines.append("")

# Группируем по месяцам
months = {
    "01": "📅 Январь",
    "02": "📅 Февраль",
    "03": "📅 Март",
    "04": "📅 Апрель",
    "05": "📅 Май",
    "06": "📅 Июнь",
    "07": "📅 Июль",
    "08": "📅 Август",
    "09": "📅 Сентябрь",
    "10": "📅 Октябрь",
    "11": "📅 Ноябрь",
    "12": "📅 Декабрь",
}

current_month = None
for event_id, event_date, event_name in events:
    month = event_date[5:7]
    day = event_date[8:10]

    if month != current_month:
        current_month = month
        lines.append("")
        lines.append(f"── {months.get(month, month)} ──")
        lines.append("")

    lines.append(f"  {day}. {event_name}")

# Сохраняем
with open("all_events.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Done: {len(events)} events saved")
