from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)

# Создаем reply клавиатуру для редактирования таблицы с событиями
main_reply_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='📝 Додати подію'),
    KeyboardButton(text='🧺 Видалити подію')],
    [KeyboardButton(text='🧺 Видалити всю таблицю')],
    [KeyboardButton(text="🔑 Увійти як адмін")]
],
    resize_keyboard=True, one_time_keyboard=True)

# Создаем инлайн клавиатуру для выборки событий
main_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📆 Події на сьогодні', callback_data='today'),
     InlineKeyboardButton(text='📅 Події на завтра', callback_data='tomorrow')],
    [InlineKeyboardButton(text='📅 Події на поточний місяць', callback_data='this_month'),
     InlineKeyboardButton(text='📅 Події на наступний місяць', callback_data='next_month')],
    [InlineKeyboardButton(text='Вивести всі події', callback_data='all_events')]
])


# Создаёт клавиатуру с кнопками «Назад» и «Далі»
def get_pagination_keyboard(page: int, total_events: int):
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"events_page:{page - 1}"))
    if (page + 1) * 5 < total_events:
        keyboard.append(InlineKeyboardButton(text="➡️ Далі", callback_data=f"events_page:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None


# Клавиатура для администратора
admin_panel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Список користувачів")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📤 Експорт в Excel")],
        [KeyboardButton(text="🚪 Вийти")]
    ],
    resize_keyboard=True, one_time_keyboard=True
)