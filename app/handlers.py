from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.keyboards import main_reply_kb

import sqlite3

import app.keyboards as kb
import app.functions as f

# Создаем объект роутера
router = Router()

# # Список ID администраторов (можно будет заполнять при логине)
# admin_users = set()

# Создание класса FSM для регистрации нового события
class Reg(StatesGroup):
    event_date = State()
    event_name = State()

# Создание класса FSM для удаления события
class Del(StatesGroup):
    event_id = State()
    event_agreed = State()

# Создание класса FSM для удаления таблицы
class Delt(StatesGroup):
    del_agreed = State()

# Создание класса FSM для входа в админ-панель
class Admin(StatesGroup):
    password = State()


# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_table_name = f"user_{message.from_user.id}"  # Generate table name based on user id
    connection = sqlite3.connect('./app/my_db.sql')
    try:
        cur = connection.cursor()
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{user_table_name}';"
        cur.execute(query)
        table_exists = cur.fetchone()
        if table_exists:
            await message.answer("Ви вже користувались цим ботом, тому Ваша таблиця вже була створена.\n"
                                 "Можете продовжити користуватись нею.", reply_markup=kb.main_reply_kb)
            await message.answer("Можете переглянути події.", reply_markup=kb.main_inline_kb)
            return
        else:
            cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {user_table_name} (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date datetime DEFAULT NULL,
                event_name text
            )
        """)
        connection.commit()
        await message.answer(f"Шановний {message.from_user.first_name},"
                             f" для Вас створена таблиця Ваших подій під назвою {user_table_name}.\n"
                             f"Формат полів таблиці:\n"
                             f"1. Умовний номер події.\n"
                             f"2. Дата події.\n"
                             f"3. Назва події.",
                             reply_markup=kb.main_reply_kb)
    except sqlite3.Error as e:
        await message.answer("Сталася помилка при створенні бази даних. Спробуйте пізніше.\n"
                             f"Код помилки: {e}")
    finally:
        connection.close()

# Переименование таблицы
# @router.message(Command('rename'))
# async def cmd_rename(message: Message):
#     user_table_name = f"user_{message.from_user.id}"  # Generate table name based on user id
#     connection = sqlite3.connect('./app/my_db.sql')
#     try:
#         cur = connection.cursor()
#         query = f"ALTER TABLE date RENAME TO user_1438974394;"
#         cur.execute(query)
#         connection.commit()
#         await message.answer("Таблица переименована")
#     except sqlite3.Error as e:
#         await message.answer("Сталася помилка.\n"
#                              f"Код помилки: {e}")
#     finally:
#         connection.close()

# Обработчик команды на вход в админ-панель
@router.message(F.text == '🔑 Увійти як адмін')
async def admin_login_one(message: Message, state: FSMContext):
    await state.set_state(Admin.password)
    await message.answer("Введіть пароль адміністратора:")

@router.message(Admin.password)
async def admin_login_two(message: Message, state: FSMContext):
    if await f.check_admin_password(message.text):
        # admin_users.add(message.from_user.id)
        await message.answer("✅ Ви успішно ввійшли в адмін-панель.")
        await message.answer("Можете користуватись всіма можливостями адмін-панелі.", reply_markup=kb.admin_panel_kb)
        await state.clear()
    else:
        await message.answer("❌ Пароль адміністратора хибний. Спробуйте знову.")


"""Обработчики для админ-панели"""
# Обработчик нажатия на кнопку экспорта
@router.message(F.text == '📤 Експорт в Excel')
async def export_users_data(message: Message):
    user_db = await f.get_users_dict() # {12345: 5, 67890: 8}
    file_path = await f.export_to_excel(user_db)
    document = FSInputFile(file_path)

    await message.answer_document(document, caption="📂 Дані користувачів експортовано в Excel.")

# Обработчик для вывода статистики
@router.message(F.text == '📊 Статистика')
async def get_statistic(message: Message):
    users_db = await f.get_users_dict()
    users_events = '\n'.join(' - '.join([str(user_id), str(event) + ' подій']) for user_id, event in users_db.items())
    await message.answer("Статистика користувачів:\n"
                         f"{users_events}")

# Обработчик для вывода списка пользователей
@router.message(F.text == '👥 Список користувачів')
async def get_users_list(message: Message):
    users_db = await f.get_user_ids()
    users_list = '\n'.join(str(user_id) for user_id in users_db)
    await message.answer("Список ID користувачів:\n"
                         f"{users_list}")

# Обработчик для выхода из админ-панели
@router.message(F.text == '🚪 Вийти')
async def admin_logout(message: Message):
    await message.answer('Ви вийшли з адмін-панелі', reply_markup=main_reply_kb)
    # await message.answer(reply_markup=main_reply_kb)


"""Обработчики для менюшки пользователя добавления/удаления события и таблицы целиком"""
# Добавление события в таблицу
@router.message(F.text == '📝 Додати подію')
async def add_event_one(message: Message, state: FSMContext):
    await state.set_state(Reg.event_date)
    await message.answer("Введіть дату події в форматі: YYYY-MM-DD")

@router.message(Reg.event_date)
async def add_event_two(message: Message, state: FSMContext):
    if await f.validate_date(message.text):
        await state.update_data(event_date=message.text)
        await state.set_state(Reg.event_name)
        await message.answer("Введіть назву події:")
    else:
        await state.set_state(Reg.event_date)
        await message.answer("Невірний формат дати. Введіть дату знову в форматі: YYYY-MM-DD")

@router.message(Reg.event_name)
async def add_event_three(message: Message, state: FSMContext):
    await state.update_data(event_name=message.text)
    data = await state.get_data()
    table_name = f"user_{message.from_user.id}"
    query = f"INSERT INTO {table_name} (event_date, event_name) VALUES (?, ?)"
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()
    try:
        cur.execute(query, (data['event_date'], data['event_name']))
        connection.commit()
        await message.answer('Подія успішно додана!\n'
                             f'{data["event_date"]} - {data["event_name"]}', reply_markup=kb.main_inline_kb)
    except sqlite3.Error as e:
        await message.answer(f'Помилка при додаванні події: {e}')
    finally:
        connection.close()  # Закрываем соединение
    await state.clear() # Очищаем состояние


# Удаление события из таблицы
@router.message(F.text == '🧺 Видалити подію')
async def del_event_one(message: Message, state: FSMContext):
    await state.set_state(Del.event_id)
    await message.answer("Введіть ID події, яку треба видалити:")

@router.message(Del.event_id)
async def del_event_two(message: Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(event_id=message.text)
        await state.set_state(Del.event_agreed)
        await message.answer(f"Ви підтверджуєте видалення подіїї з ID - {message.text}? (y/any)")
    else:
        await message.answer("ID події має бути числом. Спробуйте ввести ID події ще раз:")

@router.message(Del.event_agreed)
async def del_event_three(message: Message, state: FSMContext):
    await state.update_data(event_agreed=message.text)
    data = await state.get_data()
    if data['event_agreed'] == 'y':
        table_name = f"user_{message.from_user.id}"
        query = f"DELETE FROM {table_name} WHERE event_id = ?"
        connection = sqlite3.connect('./app/my_db.sql')
        cur = connection.cursor()
        try:
            cur.execute(query, (data['event_id'],))
            connection.commit()
            if cur.rowcount > 0: # Проверка, что что-то удалилось
                await message.answer(f'Подія з ID {data["event_id"]} успішно видалена!'
                                 , reply_markup=kb.main_inline_kb)
                await state.clear()  # Очищаем состояние
            else:
                await message.answer("Події з таким ID не існує). Спробуйте ввести ID події ще раз:")
        except sqlite3.Error as e:
            await message.answer(f'Помилка при видаленні події: {e}')
        finally:
            connection.close()  # Закрываем соединение
    else:
        await message.answer(f"Видалення події з ID - {data['event_id']} не підтверджено.")
        await state.clear()  # Очищаем состояние


# Удаление всей таблицы пользователя
@router.message(F.text == '🧺 Видалити всю таблицю')
async def del_table_one(message: Message, state: FSMContext):
    await state.set_state(Delt.del_agreed)
    await message.answer("Ви підтверджуєте видалення таблиці? (y/any)")

@router.message(Delt.del_agreed)
async def del_table_two(message: Message, state: FSMContext):
    if message.text == 'y':
        table_name = f"user_{message.from_user.id}"
        query = f"DROP TABLE IF EXISTS {table_name};"
        connection = sqlite3.connect('./app/my_db.sql')
        cur = connection.cursor()
        try:
            cur.execute(query)
            connection.commit()
            await message.answer(f'Ваша таблица подій успішно видалена!\n'
                                 f'Для створення нової таблиці введіть або натисність /start')
            await state.clear()  # Очищаем состояние
        except sqlite3.Error as e:
            await message.answer(f'Помилка при видаленні події: {e}')
            await state.clear()  # Очищаем состояние
        finally:
            connection.close()  # Закрываем соединение
            await state.clear()  # Очищаем состояние
    else:
        await message.answer('Удаление таблицы не подтверждено!!!')
        await state.clear()  # Очищаем состояние


"""Обработчики для событий сегодня - завтра - в этом месяце - в следующем месяце"""
# Обработчик колбэка от инлайн кнопки, выборка событий на сегодня
@router.callback_query(F.data == 'today')
async def catalog(callback: CallbackQuery):
    await callback.message.delete()  # Удаляем последнее сообщение, чтоб на его месте отправить новое
    # print(await f.get_events_for_today(user_id=1438974394))
    table_name = f"user_{callback.from_user.id}"
    query = f"""
    SELECT event_id AS Номер,
        STRFTIME('%d-%m-%Y', event_date) AS Дата,
        event_name AS Событие,
        CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
    FROM {table_name}
    WHERE CAST(STRFTIME('%m%d', event_date) AS INTEGER) = CAST(STRFTIME('%m%d', DATE('now', '+2 hour')) AS INTEGER)
    ORDER BY strftime('%m-%d', event_date), event_date;
"""
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()

    # Выполнение запроса
    cur.execute(query)
    events = cur.fetchall()
    events_text = '\n\n'.join(['\n'.join(map(str, event)) for event in events])
    if events:
        await callback.message.answer('Події на сьогодні:\n\n' + events_text, reply_markup=kb.main_inline_kb)
    else:
        await callback.message.answer('Події на сьогодні відсутні', reply_markup=kb.main_inline_kb)

# Обработчик колбэка от инлайн кнопки, выборка событий на завтра
@router.callback_query(F.data == 'tomorrow')
async def catalog(callback: CallbackQuery):
    await callback.message.delete()  # Удаляем последнее сообщение, чтоб на его месте отправить новое
    table_name = f"user_{callback.from_user.id}"
    query = f"""
    SELECT event_id AS Номер,
        STRFTIME('%d-%m-%Y', event_date) AS Дата,
        event_name AS Событие,
        CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
    FROM {table_name}
    WHERE STRFTIME('%m%d', event_date) = STRFTIME('%m%d', DATE('now', '+26 hour'))
    ORDER BY strftime('%m-%d', event_date), event_date;
"""
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()

    # Выполнение запроса
    cur.execute(query)
    events = cur.fetchall()
    events_text = '\n\n'.join(['\n'.join(map(str, event)) for event in events])
    if events:
        await callback.message.answer('Події на завтра:\n\n' + events_text, reply_markup=kb.main_inline_kb)
    else:
        await callback.message.answer('Події на завтра відсутні', reply_markup=kb.main_inline_kb)

# Обработчик колбэка от инлайн кнопки, выборка событий на этот месяц
@router.callback_query(F.data == 'this_month')
async def catalog(callback: CallbackQuery):
    await callback.message.delete()  # Удаляем последнее сообщение, чтоб на его месте отправить новое
    table_name = f"user_{callback.from_user.id}"
    query = f"""
    SELECT event_id AS Номер,
        STRFTIME('%d-%m-%Y', event_date) AS Дата,
        event_name AS Событие,
        CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
    FROM {table_name}
    WHERE CAST(STRFTIME('%m', event_date) AS INTEGER) = CAST(STRFTIME('%m', DATE('now')) AS INTEGER)
    ORDER BY strftime('%m-%d', event_date), event_date;
"""
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()

    # Выполнение запроса
    cur.execute(query)
    events = cur.fetchall()
    events_text = '\n\n'.join(['\n'.join(map(str, event)) for event in events])
    if events:
        await callback.message.answer('Події на поточний місяць:\n\n' + events_text, reply_markup=kb.main_inline_kb)
    else:
        await callback.message.answer('Події в цьому місяці відсутні', reply_markup=kb.main_inline_kb)

# Обработчик колбэка от инлайн кнопки, выборка событий на следующий месяц
@router.callback_query(F.data == 'next_month')
async def catalog(callback: CallbackQuery):
    await callback.message.delete()  # Удаляем последнее сообщение, чтоб на его месте отправить новое
    table_name = f"user_{callback.from_user.id}"
    query = f"""
    SELECT event_id AS Номер,
        STRFTIME('%d-%m-%Y', event_date) AS Дата,
        event_name AS Событие,
        CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
    FROM {table_name}
    WHERE STRFTIME('%m', event_date) = STRFTIME('%m', DATE('now', '+1 month'))
    ORDER BY strftime('%m-%d', event_date), event_date;
"""
    connection = sqlite3.connect('./app/my_db.sql')
    cur = connection.cursor()

    # Выполнение запроса
    cur.execute(query)
    events = cur.fetchall()
    events_text = '\n\n'.join(['\n'.join(map(str, event)) for event in events])
    if events:
        await callback.message.answer('Події на наступний місяць:\n\n' + events_text, reply_markup=kb.main_inline_kb)
    else:
        await callback.message.answer('Події на наступний місяць відсутні', reply_markup=kb.main_inline_kb)


"""Обработчики для всех событий постранично по 5 событий"""
# Обработчик для вывода первых 5 событий
@router.callback_query(F.data == "all_events")
async def show_events(callback: CallbackQuery):
    # await callback.message.delete() # Удаляем последнее сообщение, чтоб на его месте отправить новое
    await callback.answer()
    events = await f.get_events(callback.from_user.id)
    # print(events)  # Посмотрим, что реально приходит
    if not events:
        await callback.message.answer("У вас поки що немає подій.")
        return
    await send_events_page(callback.message, events, page=0)

async def send_events_page(message, events, page):
    """Выводит страницу событий"""
    start = page * 5
    end = start + 5
    events_page = events[start:end]

    text = "\n".join([f"🔹 ID: {e[0]} | {e[1]} | {e[2]}" for e in events_page])
    text = f"📌 Ваші події (сторінка {page+1}):\n\n" + text

    keyboard = kb.get_pagination_keyboard(page, len(events))

    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("events_page:"))
async def paginate_events(callback: CallbackQuery):
    """Обработчик для кнопок пагинации"""
    page = int(callback.data.split(":")[1])
    events = await f.get_events(callback.from_user.id)

    await callback.message.edit_text(
        text=f"📌 Ваші події (сторінка {page+1}):\n\n" +
             "\n".join([f"🔹 ID: {e[0]} | {e[1]} | {e[2]}" for e in events[page*5:(page+1)*5]]),
        reply_markup=kb.get_pagination_keyboard(page, len(events))
    )
    await callback.answer()