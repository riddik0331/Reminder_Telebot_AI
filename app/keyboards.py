from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# Main reply keyboard with quick add buttons
main_reply_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📝 Додати подію"),
            KeyboardButton(text="🧺 Видалити подію"),
        ],
        [
            KeyboardButton(text="🔍 Пошук події"),
            KeyboardButton(text="🧺 Видалити всю таблицю"),
        ],
        [
            KeyboardButton(text="➕ Сьогодні"),
            KeyboardButton(text="➕ Завтра"),
            KeyboardButton(text="➕ Через тиждень"),
        ],
        [KeyboardButton(text="🔑 Увійти як адмін")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


# Inline keyboard for viewing events
main_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📆 Події на сьогодні", callback_data="today"),
            InlineKeyboardButton(text="📅 Події на завтра", callback_data="tomorrow"),
        ],
        [
            InlineKeyboardButton(
                text="📅 Події на поточний місяць", callback_data="this_month"
            ),
            InlineKeyboardButton(
                text="📅 Події на наступний місяць", callback_data="next_month"
            ),
        ],
        [InlineKeyboardButton(text="📋 Всі події", callback_data="all_events")],
        [
            InlineKeyboardButton(
                text="📊 Дайджест місяця", callback_data="monthly_digest"
            )
        ],
        [
            InlineKeyboardButton(text="📥 Експорт", callback_data="export_menu"),
        ],
    ]
)

# Export menu keyboard
export_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 JSON", callback_data="export_json"),
            InlineKeyboardButton(text="📊 CSV", callback_data="export_csv"),
        ],
        [
            InlineKeyboardButton(text="📅 iCal", callback_data="export_ical"),
            InlineKeyboardButton(text="📝 TXT", callback_data="export_txt"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"),
        ],
    ]
)


def get_pagination_keyboard(page: int, total_events: int) -> InlineKeyboardMarkup:
    """Create keyboard with Back and Next buttons."""
    keyboard = []
    if page > 0:
        keyboard.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"events_page:{page - 1}"
            )
        )
    if (page + 1) * 5 < total_events:
        keyboard.append(
            InlineKeyboardButton(text="➡️ Далі", callback_data=f"events_page:{page + 1}")
        )
    return InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None


# Admin panel keyboard
admin_panel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Список користувачів")],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="📤 Експорт в Excel"),
        ],
        [
            KeyboardButton(text="📄 Експорт JSON"),
            KeyboardButton(text="📊 Експорт CSV"),
        ],
        [
            KeyboardButton(text="📅 Експорт iCal"),
            KeyboardButton(text="📝 Експорт TXT"),
        ],
        [KeyboardButton(text="🚪 Вийти")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)
