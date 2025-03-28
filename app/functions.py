import re
import sqlite3
from datetime import datetime

import pandas as pd

from config import ADMIN_PASSWORD


# Функция проверки правильности формата ввода даты события
async def validate_date(date_str):
    try:
        # Попытка преобразовать строку в объект datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        # Если формат не совпадает, будет выброшено исключение
        return False


# Функция для получения всех событий пользователя
async def get_events(user_id):
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()
    table_name = f"user_{user_id}"
    try:
        cur.execute(f"SELECT * FROM {table_name} ORDER BY strftime('%m-%d', event_date), event_date;")
        events = cur.fetchall()
    except sqlite3.Error as e:
        events = []
    finally:
        connection.close()
    return events


# Функция для получения событий на сегодня (пример)
async def get_events_for_today(user_id: int):
    table_name = f"user_{user_id}"
    query = f"""
        SELECT event_id AS Номер,
            STRFTIME('%d-%m-%Y', event_date) AS Дата,
            event_name AS Событие,
            CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
        FROM {table_name}
        WHERE CAST(STRFTIME('%m%d', event_date) AS INTEGER) = CAST(STRFTIME('%m%d', DATE('now', '+2 hour')) AS INTEGER);
    """
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()
    # Выполнение запроса
    cur.execute(query)
    events = cur.fetchall()
    events_text = '\n\n'.join(['\n'.join(map(str, event)) for event in events])
    return events_text


# Функция получения списка пользователей бота
async def get_user_ids():
    # Логика получения всех пользователей из базы данных
    user_ids = []
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'user_%';"
    cur.execute(query)
    users_list = cur.fetchall()
    for row in users_list:
        table_name = row[0]
        match = re.match(r"user_(\d+)", table_name)
        if match:
            user_ids.append(int(match.group(1)))  # Преобразуем в int
    connection.close()
    return user_ids


# # Функция, которая будет отправлять события
async def send_daily_events(bot):
    for user_id in await get_user_ids():
        events = await get_events_for_today(user_id)  # Эта функция должна вернуть список событий на сегодняшний день
        if events:
            await bot.send_message(user_id, f"📅 Події на сьогодні:\n{events}")
        else:
            await bot.send_message(user_id, "📅 На сьогодні події відсутні.")


# Функция для проверки пароля администратора
async def check_admin_password(password: str) -> bool:
    if password == ADMIN_PASSWORD:
        return True
    return False


# Функция для получения данных из БД о пользователях и количестве их событий
async def get_users_dict() -> dict:
    users_dict = {}  # Словарь для хранения пользователей и их количества событий
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()
    user_ids = await get_user_ids()
    for user_id in user_ids:
        cur.execute(f"SELECT COUNT(*) FROM user_{user_id}")
        user_count = cur.fetchone()[0]
        users_dict[user_id] = user_count
    connection.close()
    return users_dict


# Функция для экспорта в Excel
async def export_to_excel(users_db):
    # Создаем список для хранения данных
    user_data = []

    # Проходим по каждому пользователю и добавляем его данные в список
    for user_id, user_info in users_db.items():
        user_data.append({
            "ID користувача": user_id,
            "Кількість подій": user_info
        })

    # Создаем DataFrame из списка
    df = pd.DataFrame(user_data)

    # Указываем путь для сохранения Excel файла
    file_path = "users_data.xlsx"

    # Экспортируем данные в Excel
    df.to_excel(file_path, index=False, engine='openpyxl')

    return file_path  # Возвращаем путь к сохраненному файлу
