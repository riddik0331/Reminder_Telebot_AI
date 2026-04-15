from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import re

import app.keyboards as kb
import app.database as db

# Creating router object
router = Router()

# Category emojis for display
CATEGORY_EMOJI = {
    "birthday": "🎂",
    "holiday": "🎉",
    "deadline": "⚠️",
    "meeting": "🤝",
    "reminder": "📌",
    "anniversary": "💍",
    "other": "📅",
}


def get_category_emoji(category: str) -> str:
    """Get emoji for event category."""
    return CATEGORY_EMOJI.get(category, "📅")


# FSM States for adding new event
class Reg(StatesGroup):
    event_date = State()
    event_name = State()
    confirm = State()


# FSM States for editing event
class Edit(StatesGroup):
    event_id = State()
    new_date = State()
    new_name = State()


# FSM States for deleting event
class Del(StatesGroup):
    event_id = State()
    event_agreed = State()


# FSM States for deleting all events
class Delt(StatesGroup):
    del_agreed = State()


# FSM States for admin login
class Admin(StatesGroup):
    password = State()


# FSM States for event search
class Search(StatesGroup):
    key_word = State()


# FSM States for search pagination (stores results for page navigation)
class SearchPage(StatesGroup):
    query = State()  # Search query string
    page = State()  # Current page number


# In-memory cache for search results (keyed by user_id)
# This is simpler than storing full results in FSM
_search_cache: dict[int, list] = {}


async def find_similar_events(user_id: int, event_name: str, limit: int = 3) -> list:
    """
    Find similar events to suggest they might be duplicates.

    Uses fuzzy search with lower threshold to find similar names.

    Args:
        user_id: User ID
        event_name: Event name to compare
        limit: Maximum number of similar events to return

    Returns:
        List of tuples (event_id, event_date, event_name, score)
    """
    from rapidfuzz import fuzz

    events = await db.get_events(user_id)
    if not events:
        return []

    event_name_lower = event_name.lower().strip()
    results = []

    for event in events:
        event_id = event[0]
        event_date = event[1]
        existing_name = event[2]
        existing_name_lower = existing_name.lower()

        # Calculate similarity
        # Use both exact substring and fuzzy match
        similarity = 0

        # 1. Check if one contains the other (high similarity)
        if (
            event_name_lower in existing_name_lower
            or existing_name_lower in event_name_lower
        ):
            similarity = 95

        # 2. Check word-level similarity
        else:
            words = existing_name_lower.split()
            for word in words:
                if len(word) >= 3:
                    # Compare with beginning of word
                    compare_len = min(len(event_name_lower), len(word))
                    word_prefix = word[:compare_len]
                    score = fuzz.ratio(event_name_lower, word_prefix)
                    similarity = max(similarity, score)

        # Accept if similarity >= 70%
        if similarity >= 70:
            results.append((event_id, event_date, existing_name, similarity))

    # Sort by similarity and return top results
    results.sort(key=lambda x: -x[3])
    return results[:limit]


async def send_search_page(
    message_or_callback,
    query: str,
    events: list,
    page: int = 0,
    page_size: int = 10,
    update: bool = False,
):
    """
    Send a page of search results with pagination keyboard.

    Args:
        message_or_callback: Message or CallbackQuery object
        query: Search query string
        events: List of events (tuples with id, date, name, anniversary)
        page: Page number (0-indexed)
        page_size: Items per page
        update: If True, edit existing message; if False, send new one
    """
    total = len(events)
    total_pages = (total + page_size - 1) // page_size

    # Calculate slice for current page
    start = page * page_size
    end = min(start + page_size, total)
    page_events = events[start:end]

    # Format results with category emoji and local_id
    result_lines = []
    for e in page_events:
        emoji = get_category_emoji(e[4]) if len(e) > 4 else "📅"
        local_id = e[5] if len(e) > 5 else e[0]
        result_lines.append(f"{emoji} #{local_id} | {e[1]} | {e[2][:35]}")
    result_text = "\n".join(result_lines)

    # Create pagination keyboard
    keyboard = get_search_pagination_keyboard(page, total, page_size)

    text = (
        f"🔍 *Результаты '{query}':*\n"
        f"📊 Найдено: *{total}*\n"
        f"📄 Страница {page + 1}/{total_pages}\n\n"
        f"{result_text}"
    )

    try:
        if update and hasattr(message_or_callback, "message"):
            await message_or_callback.message.edit_text(
                text, parse_mode="Markdown", reply_markup=keyboard
            )
        else:
            await message_or_callback.answer(
                text, parse_mode="Markdown", reply_markup=keyboard
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass  # Ignore - no changes needed
        else:
            raise


# FSM States for setting reminder days
class Remind(StatesGroup):
    event_id = State()
    days = State()


# FSM States for confirming similar events
class SimilarConfirm(StatesGroup):
    """State for confirming addition when similar events exist."""

    event_date = State()
    event_name = State()
    similar_events = State()  # Store IDs of similar events


# ==================== COMMAND HANDLERS ====================


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    try:
        # Add or update user in database
        await db.add_user(user_id, username, first_name, last_name)

        user_events = await db.get_events(user_id, limit=1)

        if user_events:
            await message.answer(
                f"👋 Привіт, {message.from_user.first_name}!\n\n"
                "Ласкаво просимо назад до боту-нагадувача!\n"
                "Ви вже маєте події у базі даних.",
                reply_markup=kb.main_reply_kb,
            )
        else:
            await message.answer(
                f"👋 Привіт, {message.from_user.first_name}!\n\n"
                "Я бот-нагадувач про події.\n"
                "Додавайте свої події, і я буду нагадувати вам про них!\n\n"
                "Використовуйте меню нижче для навігації.",
                reply_markup=kb.main_reply_kb,
            )

        await message.answer("Оберіть дію:", reply_markup=kb.main_inline_kb)

    except Exception as e:
        await message.answer(f"Сталася помилка: {e}")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📚 *Допомога*

Ось доступні команди:

*Основні:*
/start - Перезапустити бота
/help - Показати цю довідку

*Події:*
📝 Додати подію - додати нову подію
🧺 Видалити подію - видалити подію за ID
🔍 Пошук події - знайти подію за ключовим словом

*Перегляд:*
📆 Події на сьогодні
📅 Події на завтра  
📅 Події на поточний місяць
📅 Події на наступний місяць
📋 Всі події (з пагінацією)

*Швидкі кнопки:*
➕ Сьогодні - додати подію на сьогодні
➕ Завтра - додати подію на завтра
➕ Через тиждень - додати подію через 7 днів

*Адмін:*
🔑 Увійти як адмін - вхід в адмін-панель
"""
    await message.answer(
        help_text, parse_mode="Markdown", reply_markup=kb.main_reply_kb
    )


# ==================== ADMIN HANDLERS ====================


@router.message(F.text == "🔑 Увійти як адмін")
async def admin_login_one(message: Message, state: FSMContext):
    await state.set_state(Admin.password)
    await message.answer("🔐 Введіть пароль адміністратора:")


@router.message(Admin.password)
async def admin_login_two(message: Message, state: FSMContext):
    from config import ADMIN_PASSWORD

    if await db.check_admin_password(message.text, ADMIN_PASSWORD):
        await message.answer(
            "✅ *Ви успішно ввійшли в адмін-панель.*", parse_mode="Markdown"
        )
        await message.answer(
            "Можете користуватись всіма можливостями:", reply_markup=kb.admin_panel_kb
        )
        await state.clear()
    else:
        await message.answer("❌ Пароль хибний. Спробуйте ще раз.")


@router.message(F.text == "📤 Експорт в Excel")
async def export_users_data(message: Message):
    try:
        from app.functions import export_to_excel

        users_db = await db.get_users_stats()
        file_path = await export_to_excel(users_db)
        document = FSInputFile(file_path)
        await message.answer_document(document, caption="📂 Дані експортовано в Excel.")
    except Exception as e:
        await message.answer(f"Помилка експорту: {e}")


@router.message(F.text == "☁️ Бекап на Google Drive")
async def backup_to_drive(message: Message):
    """Create backup of database to Google Drive."""
    await message.answer("☁️ Створюю бекап на Google Drive...\n\n⏳ Зачекайте...")

    from app.google_drive_backup import backup_database_to_drive, is_drive_configured

    if not is_drive_configured():
        await message.answer(
            "❌ *Google Drive не налаштовано*\n\n"
            "Для настройки:\n"
            "1. Створи проект у [Google Cloud Console](https://console.cloud.google.com/)\n"
            "2. Увімкни Google Drive API\n"
            "3. Створи OAuth 2.0 credentials\n"
            "4. Скачай credentials.json у папку з ботом\n"
            "5. Перезапусти бота",
            parse_mode="Markdown",
        )
        return

    result = await backup_database_to_drive()
    await message.answer(result["message"], parse_mode="Markdown")


@router.message(F.text == "📂 Список бекапів")
async def list_backups(message: Message):
    """Show list of backups on Google Drive."""
    await message.answer("📂 Шукаю бекапи на Google Drive...\n\n⏳ Зачекайте...")

    from app.google_drive_backup import list_backups, is_drive_configured

    if not is_drive_configured():
        await message.answer(
            "❌ *Google Drive не налаштовано*\n\n"
            "Для настройки виконай кроки з 'Бекап на Google Drive'",
            parse_mode="Markdown",
        )
        return

    result = await list_backups()
    await message.answer(result["message"], parse_mode="Markdown")


@router.message(F.text == "📊 Статистика")
async def get_statistic(message: Message):
    try:
        users_db = await db.get_users_stats()
        if not users_db:
            await message.answer("📊 Статистика пуста - немає користувачів.")
            return

        total_events = sum(users_db.values())
        total_users = len(users_db)

        stats_text = f"""
📊 *Статистика бота:*

👥 Користувачів: {total_users}
📝 Всього подій: {total_events}
📈 Середнє подій на користувача: {total_events / total_users:.1f}

*Детальніше:*
"""
        for user_id, count in list(users_db.items())[:10]:
            stats_text += f"\n`{user_id}` - {count} подій"

        if len(users_db) > 10:
            stats_text += f"\n... та ще {len(users_db) - 10} користувачів"

        await message.answer(stats_text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Помилка: {e}")


@router.message(F.text == "👥 Список користувачів")
async def get_users_list(message: Message):
    try:
        user_ids = await db.get_user_ids()
        if not user_ids:
            await message.answer("Список користувачів пустий.")
            return

        users_list = "\n".join(str(uid) for uid in user_ids)
        await message.answer(
            f"👥 *Список ID:*\n\n`{users_list}`", parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"Помилка: {e}")


@router.message(F.text == "🚪 Вийти")
async def admin_logout(message: Message):
    await message.answer("✅ Ви вийшли з адмін-панелі", reply_markup=kb.main_reply_kb)


# ==================== ADD EVENT HANDLERS ====================


@router.message(F.text == "📝 Додати подію")
async def add_event_one(message: Message, state: FSMContext):
    await state.set_state(Reg.event_date)
    await message.answer(
        "📝 *Додавання нової події*\n\n"
        "Введіть дату події:\n"
        "• Формат: YYYY-MM-DD (2024-12-25)\n"
        "• Або природною мовою: 'через тиждень', 'завтра', 'в понедельник'\n\n"
        "💡 Або просто напишіть: 'встреча завтра' або 'день рождения мамы через неделю'",
        parse_mode="Markdown",
    )


@router.message(Reg.event_date)
async def add_event_two(message: Message, state: FSMContext):
    from app.ai_helper import ai, parse_date_fallback

    user_input = message.text.strip()
    user_id = message.from_user.id

    # Проверяем естественный ввод типа "встреча завтра"
    natural_patterns = ["завтра", "сегодня", "послезавтра", "через"]
    is_natural = any(p in user_input.lower() for p in natural_patterns)

    parsed_date = None
    event_name = None

    # Пробуем AI парсинг для естественного ввода
    if is_natural and ai.available:
        parsed = await ai.parse_full_event_input(user_input)
        if parsed and parsed.get("name") and parsed.get("date"):
            parsed_date = parsed["date"]
            event_name = parsed["name"]

    # Если AI не справился, пробуем парсить дату
    if not parsed_date:
        # Пробуем AI парсинг даты
        parsed_date = await ai.parse_date_from_text(user_input)

        # Fallback к ручному парсингу
        if not parsed_date:
            from app.functions import validate_date

            if await validate_date(user_input):
                parsed_date = user_input
            else:
                parsed_date = await parse_date_fallback(user_input)

        # Если это был естественный ввод, извлекаем название
        if is_natural and parsed_date:
            event_name = user_input
            # Убираем дату из названия
            for kw in ["завтра", "сегодня", "послезавтра"]:
                event_name = re.sub(
                    rf"\b{kw}\b", "", event_name, flags=re.IGNORECASE
                ).strip()
            event_name = re.sub(
                r"через\s+\d+\s+(дн|дня|дней|недел|неделю|місяць|месяц)",
                "",
                event_name,
                flags=re.IGNORECASE,
            ).strip()
            event_name = re.sub(
                r"в\s+(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)",
                "",
                event_name,
                flags=re.IGNORECASE,
            ).strip()

    if parsed_date:
        await state.update_data(event_date=parsed_date)

        if event_name and len(event_name) > 1:
            # Проверяем похожие события
            similar = await find_similar_events(user_id, event_name)

            if similar:
                # Сохраняем данные для добавления после подтверждения
                await state.update_data(event_name=event_name)
                await state.set_state(SimilarConfirm.event_date)

                # Формируем сообщение с похожими событиями
                similar_text = "\n".join(f"   • {e[2][:45]}" for e in similar)

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Додати все одно", callback_data="similar_add"
                            ),
                            InlineKeyboardButton(
                                text="❌ Скасувати", callback_data="similar_cancel"
                            ),
                        ]
                    ]
                )

                await message.answer(
                    f"⚠️ *Можливо, схоже вже існує:*\n\n{similar_text}\n\n"
                    f"Додати '{event_name}' на {parsed_date}?",
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            else:
                # Нет похожих - добавляем сразу
                from app.ai_helper import ai

                category = await ai.categorize_event(event_name)
                emoji = get_category_emoji(category)
                result = await db.add_event(user_id, parsed_date, event_name, category)
                await state.clear()
                if result:
                    global_id, local_id = result
                    await message.answer(
                        f"✅ *Подія додана!*\n\n"
                        f"🆔 #{local_id}\n"
                        f"{emoji} {event_name}\n"
                        f"📅 {parsed_date}",
                        parse_mode="Markdown",
                        reply_markup=kb.main_inline_kb,
                    )
                else:
                    await message.answer(
                        "❌ Помилка при додаванні.",
                        reply_markup=kb.main_inline_kb,
                    )
        else:
            # Запрашиваем название
            await state.set_state(Reg.event_name)
            await message.answer(f"✅ Дата: {parsed_date}\n\nВведіть назву події:")
    else:
        await message.answer(
            "❌ Не вдалося розпізнати дату.\nВведіть дату в форматі YYYY-MM-DD:"
        )


@router.message(Reg.event_name)
async def add_event_three(message: Message, state: FSMContext):
    from app.ai_helper import ai

    event_name = message.text.strip()
    user_id = message.from_user.id

    # Get event date from state
    data = await state.get_data()
    event_date = data.get("event_date", "")

    # Try AI improvement for name
    suggested_name = await ai.suggest_event_name(event_name)
    if suggested_name:
        event_name = suggested_name

    await state.update_data(event_name=event_name)

    # Check for similar events
    similar = await find_similar_events(user_id, event_name)

    if similar:
        # Save state and ask for confirmation
        await state.set_state(SimilarConfirm.event_date)

        similar_text = "\n".join(f"   • {e[2][:45]}" for e in similar)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Додати все одно", callback_data="similar_add"
                    ),
                    InlineKeyboardButton(
                        text="❌ Скасувати", callback_data="similar_cancel"
                    ),
                ]
            ]
        )

        await message.answer(
            f"⚠️ *Можливо, схоже вже існує:*\n\n{similar_text}\n\n"
            f"Додати '{event_name}' на {event_date}?",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        # No similar events - add directly
        category = await ai.categorize_event(event_name)
        emoji = get_category_emoji(category)
        result = await db.add_event(user_id, event_date, event_name, category)

        if result:
            global_id, local_id = result
            await message.answer(
                f"✅ *Подія додана!*\n\n"
                f"🆔 #{local_id}\n"
                f"{emoji} {event_name}\n"
                f"📅 {event_date}",
                parse_mode="Markdown",
                reply_markup=kb.main_inline_kb,
            )
        else:
            await message.answer("❌ Помилка при додаванні події.")

        await state.clear()


# ==================== QUICK ADD BUTTONS ====================


@router.message(F.text == "➕ Сьогодні")
async def quick_add_today(message: Message, state: FSMContext):
    from datetime import datetime
    from config import TIMEZONE

    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    await state.update_data(event_date=today)
    await state.set_state(Reg.event_name)
    await message.answer(f"✅ Дата: сьогодні ({today})\n\nВведіть назву події:")


@router.message(F.text == "➕ Завтра")
async def quick_add_tomorrow(message: Message, state: FSMContext):
    from datetime import datetime, timedelta
    from config import TIMEZONE

    tomorrow = (datetime.now(TIMEZONE) + timedelta(days=1)).strftime("%Y-%m-%d")
    await state.update_data(event_date=tomorrow)
    await state.set_state(Reg.event_name)
    await message.answer(f"✅ Дата: завтра ({tomorrow})\n\nВведіть назву події:")


@router.message(F.text == "➕ Через тиждень")
async def quick_add_week(message: Message, state: FSMContext):
    from datetime import datetime, timedelta
    from config import TIMEZONE

    week_later = (datetime.now(TIMEZONE) + timedelta(days=7)).strftime("%Y-%m-%d")
    await state.update_data(event_date=week_later)
    await state.set_state(Reg.event_name)
    await message.answer(
        f"✅ Дата: через тиждень ({week_later})\n\nВведіть назву події:"
    )


# ==================== DELETE EVENT HANDLERS ====================


@router.message(F.text == "🧺 Видалити подію")
async def del_event_one(message: Message, state: FSMContext):
    await state.set_state(Del.event_id)
    await message.answer(
        "🗑️ *Видалення подій*\n\n"
        "Введіть ID подій для видалення:\n"
        "• Один: `23`\n"
        "• Декілька: `23, 25, 27`\n"
        "• Діапазон: `23-26`\n"
        "• Змішано: `23, 25-28, 30`",
        parse_mode="Markdown",
    )


def parse_event_ids(text: str) -> list[int]:
    """
    Parse event IDs from text.
    Supports: "23", "23, 25", "23-26", "23, 25-28, 30"

    Returns list of unique IDs sorted.
    """
    import re

    text = text.strip()
    if not text:
        return []

    ids = set()

    # Split by comma
    parts = text.split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if it's a range (contains "-")
        if "-" in part:
            # Parse range like "23-26"
            range_match = re.match(r"(\d+)\s*-\s*(\d+)", part)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                if start <= end:
                    for i in range(start, end + 1):
                        ids.add(i)
        else:
            # Single ID
            if part.isdigit():
                ids.add(int(part))

    return sorted(list(ids))


@router.message(Del.event_id)
async def del_event_two(message: Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id

    # Parse IDs
    event_ids = parse_event_ids(text)

    if not event_ids:
        await message.answer(
            "❌ Не вдалося розпізнати ID.\nПриклади: `23`, `23, 25`, `23-26`",
            parse_mode="Markdown",
        )
        return

    # Limit to 50 events
    if len(event_ids) > 50:
        await message.answer(
            f"❌ Занадто багато ID ({len(event_ids)}). Максимум 50 за раз."
        )
        return

    # Get events to confirm
    events = await db.get_events_by_local_ids(user_id, event_ids)

    if not events:
        await message.answer(f"❌ Події не знайдені.\nПеревірте ID та спробуйте знову.")
        return

    # Format events for confirmation
    events_text = "\n".join(
        [f"  🗑️ #{e['local_id']} - {e['event_name']}" for e in events]
    )

    # Save to state
    await state.update_data(
        event_ids=event_ids,
        events_count=len(events),
        events_preview=events_text[:500],  # Limit preview length
    )
    await state.set_state(Del.event_agreed)

    await message.answer(
        f"❓ Ви підтверджуєте видалення {len(events)} подій?\n\n"
        f"{events_text}\n\n"
        f"Введіть 'y' для підтвердження:",
        parse_mode="Markdown",
    )


@router.message(Del.event_agreed)
async def del_event_three(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.text.lower() == "y":
        user_id = message.from_user.id
        event_ids = data.get("event_ids", [])

        if event_ids:
            # Delete multiple events
            deleted_count, deleted_ids, not_found = await db.delete_events(
                user_id, event_ids
            )

            if deleted_count > 0:
                # Format deleted IDs
                ids_text = ", ".join(f"#{id}" for id in deleted_ids)
                await message.answer(
                    f"✅ Видалено {deleted_count} подій!\n\n🗑️ {ids_text}",
                    parse_mode="Markdown",
                    reply_markup=kb.main_inline_kb,
                )
            else:
                await message.answer(
                    "❌ Не вдалося видалити події.",
                    reply_markup=kb.main_inline_kb,
                )
        else:
            await message.answer("❌ Дані втрачено. Спробуйте знову.")
    else:
        await message.answer("Видалення скасовано.")

    await state.clear()


@router.message(F.text == "🧺 Видалити всю таблицю")
async def del_table_one(message: Message, state: FSMContext):
    await state.set_state(Delt.del_agreed)
    await message.answer(
        "⚠️ *УВАГА!*\n\nВи збираєтесь видалити ВСІ ваші події.\nЦя дія незворотня!\n\nВведіть 'y' для підтвердження:",
        parse_mode="Markdown",
    )


@router.message(Delt.del_agreed)
async def del_table_two(message: Message, state: FSMContext):
    if message.text.lower() == "y":
        user_id = message.from_user.id
        success = await db.delete_user_events(user_id)

        if success:
            await message.answer(
                "✅ *Всі події успішно видалені!*\n\n"
                "Для створення нових подій використайте /start",
                parse_mode="Markdown",
            )
        else:
            await message.answer("❌ Помилка при видаленні.")
    else:
        await message.answer("Видалення скасовано.")

    await state.clear()


# ==================== SEARCH HANDLERS ====================


@router.message(F.text == "🔍 Пошук події")
async def search_event_one(message: Message, state: FSMContext):
    await state.set_state(Search.key_word)
    await message.answer(
        "🔍 *Пошук події*\n\nВведіть ключове слово:", parse_mode="Markdown"
    )


# Тестовая команда для проверки поиска
@router.message(Command("testsearch"))
async def test_search(message: Message):
    """Тестовая команда для проверки поиска."""
    user_id = message.from_user.id

    # Получаем все события
    all_events = await db.get_events(user_id)
    await message.answer(f"У тебя {len(all_events)} событий")

    # Тестовый поиск
    events = await db.search_events_fuzzy(user_id, "день")
    await message.answer(f"По запросу 'день' найдено: {len(events)} событий")


# Прямой поиск - работает по любому тексту
@router.message()
async def direct_search(message: Message, state: FSMContext):
    """Прямой поиск по ключевому слову."""
    # Пропускаем команды
    if message.text and message.text.startswith("/"):
        return

    user_id = message.from_user.id
    search_query = message.text.strip()

    # Минимум 2 символа для поиска
    if len(search_query) < 2:
        return

    try:
        # Fuzzy поиск
        events = await db.search_events_fuzzy(user_id, search_query)

        if not events:
            await message.answer(f"❌ По запросу '{search_query}' ничего не найдено")
            return

        # Сохраняем в кэш для пагинации
        _search_cache[user_id] = events

        # Сохраняем query в state для отслеживания
        await state.update_data(search_query=search_query)

        # Показываем результаты с пагинацией
        await send_search_page(message, search_query, events, page=0)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Search.key_word)
async def search_event_two(message: Message, state: FSMContext):
    """Обработка поиска через кнопку 'Пошук'."""
    try:
        user_id = message.from_user.id
        search_query = message.text.strip()

        # Получаем результаты поиска
        events = await db.search_events_fuzzy(user_id, search_query)

        if not events:
            await message.answer(f"❌ По запросу '{search_query}' ничего не найдено")
            await state.clear()
            return

        # Сохраняем в кэш для пагинации
        _search_cache[user_id] = events
        await state.update_data(search_query=search_query)

        # Показываем результаты с пагинацией
        await send_search_page(message, search_query, events, page=0)

    except TelegramBadRequest as e:
        if "message is too long" in str(e):
            await message.answer("📋 Забагато результатів, спробуйте інше слово.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

    await state.clear()


def get_search_pagination_keyboard(
    page: int, total: int, page_size: int = 10
) -> InlineKeyboardMarkup:
    """Клавиатура для пагинации поиска."""
    keyboard = []
    total_pages = (total + page_size - 1) // page_size

    # Показываем текущую страницу и навигацию
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"search_prev:{page}")
        )

    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
    )

    if (page + 1) * page_size < total:
        nav_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"search_next:{page}")
        )

    keyboard.append(nav_row)

    # Кнопка показать все
    keyboard.append(
        [
            InlineKeyboardButton(
                text=f"📋 Показать все ({total})", callback_data=f"search_all:0"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== SIMILAR EVENTS HANDLERS ====================


@router.callback_query(F.data == "similar_add", SimilarConfirm.event_date)
async def similar_add(callback: CallbackQuery, state: FSMContext):
    """Подтверждение добавления события несмотря на похожие."""
    from app.ai_helper import ai

    user_id = callback.from_user.id
    data = await state.get_data()

    event_date = data.get("event_date", "")
    event_name = data.get("event_name", "")

    if event_date and event_name:
        category = await ai.categorize_event(event_name)
        emoji = get_category_emoji(category)
        result = await db.add_event(user_id, event_date, event_name, category)

        if result:
            global_id, local_id = result
            await callback.message.edit_text(
                f"✅ *Подія додана!*\n\n"
                f"🆔 #{local_id}\n"
                f"{emoji} {event_name}\n"
                f"📅 {event_date}",
                parse_mode="Markdown",
                reply_markup=kb.main_inline_kb,
            )
        else:
            await callback.message.edit_text(
                "❌ Помилка при додаванні події.",
                reply_markup=kb.main_inline_kb,
            )
    else:
        await callback.message.edit_text(
            "❌ Дані втрачено. Спробуйте знову.",
            reply_markup=kb.main_inline_kb,
        )

    await state.clear()


@router.callback_query(F.data == "similar_cancel", SimilarConfirm.event_date)
async def similar_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления события."""
    await callback.message.edit_text(
        "❌ Додавання скасовано.",
        reply_markup=kb.main_inline_kb,
    )
    await state.clear()


# Обработчик пагинации поиска
@router.callback_query(F.data.startswith("search_"))
async def search_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработка пагинации результатов поиска."""
    data = callback.data
    user_id = callback.from_user.id

    if data.startswith("search_prev:") or data.startswith("search_next:"):
        # Определяем новую страницу
        if data.startswith("search_prev:"):
            page = int(data.split(":")[1]) - 1
        else:
            page = int(data.split(":")[1]) + 1

        # Получаем query из state
        state_data = await state.get_data()
        search_query = state_data.get("search_query", "")

        # Получаем события из кэша
        events = _search_cache.get(user_id, [])

        if not events or not search_query:
            await callback.answer(
                "❌ Результаты поиска устарели. Повторите поиск.", show_alert=True
            )
            return

        # Проверяем границы
        total_pages = (len(events) + 9) // 10  # page_size = 10
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        # Отправляем новую страницу (редактируем сообщение)
        await send_search_page(callback, search_query, events, page=page, update=True)
        await callback.answer()

    elif data.startswith("search_all:"):
        # Показать все результаты одним сообщением
        user_id = callback.from_user.id
        state_data = await state.get_data()
        search_query = state_data.get("search_query", "")
        events = _search_cache.get(user_id, [])

        if not events or not search_query:
            await callback.answer(
                "❌ Результаты поиска устарели. Повторите поиск.", show_alert=True
            )
            return

        total = len(events)
        # Format with category emoji and local_id
        result_lines = []
        for e in events:
            emoji = get_category_emoji(e[4]) if len(e) > 4 else "📅"
            local_id = e[5] if len(e) > 5 else e[0]
            result_lines.append(f"{emoji} #{local_id} | {e[1]} | {e[2][:35]}")
        result_text = "\n".join(result_lines)

        text = (
            f"🔍 *Все результаты '{search_query}':*\n"
            f"📊 Найдено: *{total}*\n\n"
            f"{result_text}"
        )

        # Удаляем старую клавиатуру пагинации
        await callback.message.edit_text(
            text, parse_mode="Markdown", reply_markup=kb.main_inline_kb
        )
        await callback.answer("📋 Показаны все результаты")


# Обработчик для кнопки-индикатора страницы (noop)
@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Обработчик пустого нажатия (индикатор страницы)."""
    await callback.answer()


# ==================== CALLBACK QUERY HANDLERS ====================


@router.callback_query(F.data == "today")
async def show_today_events(callback: CallbackQuery):
    await callback.message.delete()
    events, period_name = await db.get_events_for_period(callback.from_user.id, "today")

    if events:
        events_text = "\n\n".join(
            [f"{get_category_emoji(e[5])} #{e[4]}\n{e[3]}\n{e[2]}" for e in events]
        )
        await callback.message.answer(
            f"📆 *{period_name}:*\n\n{events_text}",
            parse_mode="Markdown",
            reply_markup=kb.main_inline_kb,
        )
    else:
        await callback.message.answer(
            f"📆 {period_name}\n\nПодії відсутні ✅", reply_markup=kb.main_inline_kb
        )


@router.callback_query(F.data == "tomorrow")
async def show_tomorrow_events(callback: CallbackQuery):
    await callback.message.delete()
    events, period_name = await db.get_events_for_period(
        callback.from_user.id, "tomorrow"
    )

    if events:
        events_text = "\n\n".join(
            [f"{get_category_emoji(e[5])} #{e[4]}\n{e[3]}\n{e[2]}" for e in events]
        )
        await callback.message.answer(
            f"📅 *{period_name}:*\n\n{events_text}",
            parse_mode="Markdown",
            reply_markup=kb.main_inline_kb,
        )
    else:
        await callback.message.answer(
            f"📅 {period_name}\n\nПодії відсутні ✅", reply_markup=kb.main_inline_kb
        )

    if events:
        events_text = "\n\n".join([f"#{e[4]}\n{e[3]}\n{e[2]}" for e in events])
        await callback.message.answer(
            f"📅 *{period_name}:*\n\n{events_text}",
            parse_mode="Markdown",
            reply_markup=kb.main_inline_kb,
        )
    else:
        await callback.message.answer(
            f"📅 {period_name}\n\nПодії відсутні ✅", reply_markup=kb.main_inline_kb
        )


@router.callback_query(F.data == "this_month")
async def show_this_month_events(callback: CallbackQuery):
    await callback.message.delete()
    events, period_name = await db.get_events_for_period(
        callback.from_user.id, "this_month"
    )

    if events:
        events_text = "\n\n".join(
            [f"{get_category_emoji(e[5])} #{e[4]}\n{e[3]}\n{e[2]}" for e in events]
        )
        await callback.message.answer(
            f"📅 *{period_name}:*\n\n{events_text}",
            parse_mode="Markdown",
            reply_markup=kb.main_inline_kb,
        )
    else:
        await callback.message.answer(
            f"📅 {period_name}\n\nПодії відсутні ✅", reply_markup=kb.main_inline_kb
        )


@router.callback_query(F.data == "next_month")
async def show_next_month_events(callback: CallbackQuery):
    await callback.message.delete()
    events, period_name = await db.get_events_for_period(
        callback.from_user.id, "next_month"
    )

    if events:
        events_text = "\n\n".join(
            [f"{get_category_emoji(e[5])} #{e[4]}\n{e[3]}\n{e[2]}" for e in events]
        )
        await callback.message.answer(
            f"📅 *{period_name}:*\n\n{events_text}",
            parse_mode="Markdown",
            reply_markup=kb.main_inline_kb,
        )
    else:
        await callback.message.answer(
            f"📅 {period_name}\n\nПодії відсутні ✅", reply_markup=kb.main_inline_kb
        )


@router.callback_query(F.data == "next_month")
async def show_next_month_events(callback: CallbackQuery):
    await callback.message.delete()
    events, period_name = await db.get_events_for_period(
        callback.from_user.id, "next_month"
    )

    if events:
        events_text = "\n\n".join([f"#{e[4]}\n{e[3]}\n{e[2]}" for e in events])
        await callback.message.answer(
            f"📅 *{period_name}:*\n\n{events_text}",
            parse_mode="Markdown",
            reply_markup=kb.main_inline_kb,
        )
    else:
        await callback.message.answer(
            f"📅 {period_name}\n\nПодії відсутні ✅", reply_markup=kb.main_inline_kb
        )


@router.callback_query(F.data == "all_events")
async def show_all_events(callback: CallbackQuery):
    await callback.answer()
    events = await db.get_events(callback.from_user.id)

    if not events:
        await callback.message.answer("У вас поки що немає подій.")
        return

    await send_events_page(callback.message, events, page=0)


@router.callback_query(F.data == "monthly_digest")
async def show_monthly_digest(callback: CallbackQuery):
    """Show monthly digest with events grouped by category."""
    from datetime import datetime
    from config import TIMEZONE
    from app.ai_helper import ai

    await callback.answer("📊 Формую дайджест...")

    user_id = callback.from_user.id
    now = datetime.now(TIMEZONE)
    year = now.year
    month = now.month

    # Get events grouped by category
    events_by_category = await db.get_events_by_category_for_month(user_id, year, month)

    # Generate digest
    digest = await ai.generate_monthly_digest(events_by_category, year, month)

    await callback.message.answer(
        digest,
        parse_mode="Markdown",
        reply_markup=kb.main_inline_kb,
    )


async def send_events_page(message, events: list, page: int):
    """Display events page with pagination."""
    start = page * 5
    end = start + 5
    events_page = events[start:end]

    if not events_page:
        return

    total = len(events)
    total_pages = (total + 4) // 5  # 5 events per page

    # Format with category emoji and local_id
    result_lines = []
    for e in events_page:
        emoji = get_category_emoji(e[4]) if len(e) > 4 else "📅"
        local_id = e[5] if len(e) > 5 else e[0]
        result_lines.append(f"{emoji} #{local_id} | {e[1]} | {e[2][:35]}")

    text = "\n".join(result_lines)
    text = (
        f"📋 *Ваші події:* всього *{total}*\n📄 Сторінка {page + 1}/{total_pages}\n\n"
        + text
    )

    keyboard = kb.get_pagination_keyboard(page, len(events))
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data.startswith("events_page:"))
async def paginate_events(callback: CallbackQuery):
    """Handle pagination buttons."""
    page = int(callback.data.split(":")[1])
    events = await db.get_events(callback.from_user.id)

    if not events:
        await callback.answer("Немає подій", show_alert=True)
        return

    total = len(events)
    total_pages = (total + 4) // 5

    start = page * 5
    end = start + 5

    # Format with category emoji and local_id
    result_lines = []
    for e in events[start:end]:
        emoji = get_category_emoji(e[4]) if len(e) > 4 else "📅"
        local_id = e[5] if len(e) > 5 else e[0]
        result_lines.append(f"{emoji} #{local_id} | {e[1]} | {e[2][:35]}")
    text = "\n".join(result_lines)

    text = (
        f"📋 *Ваші події:* всього *{total}*\n📄 Сторінка {page + 1}/{total_pages}\n\n"
        + text
    )

    keyboard = kb.get_pagination_keyboard(page, len(events))

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()
