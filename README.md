# Telegram Reminder Bot 📅

Телеграм-бот для нагадування про події та річниці.

## Можливості

- ✅ Додавання подій з датами
- ✅ Перегляд подій на сьогодні/завтра/місяць
- ✅ Пошук подій (нечіткий пошук)
- ✅ Щоденні нагадування о 9:00 (київський час)
- ✅ Адмін-панель зі статистикою та експортом в Excel
- ✅ Пагінація при перегляді всіх подій

## Встановлення

### 1. Клонуйте репозиторій

```bash
git clone <repository-url>
cd TeleBot_aiogram_testing_bot
```

### 2. Створіть віртуальне оточення

```bash
python -m venv venv
```

### 3. Активуйте віртуальне оточення

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Встановіть залежності

```bash
pip install -r requirements.txt
```

### 5. Налаштуйте змінні оточення

Створіть файл `.env` на основі `.env.example`:

```bash
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

Відредагуйте `.env` та вкажіть ваші дані:

```env
TELEBOT_TOKEN=your_bot_token_here
ADMIN_PASSWORD=your_secure_password_here
```

**Отримати токен бота:** зверніться до [@BotFather](https://t.me/BotFather) в Telegram.

### 6. Запустіть бота

```bash
python run.py
```

## Структура проекту

```
TeleBot_aiogram_testing_bot/
├── .env                 # Змінні оточення (НЕ комітити в git!)
├── .env.example         # Шаблон змінних оточення
├── .gitignore
├── requirements.txt     # Залежності Python
├── run.py              # Точка входу
├── config.py           # Конфігурація
├── bot.log             # Файл логування
├── app/
│   ├── __init__.py
│   ├── database.py     # Робота з БД (context managers, безпека)
│   ├── handlers.py     # Обробники повідомлень
│   ├── functions.py    # Допоміжні функції
│   ├── keyboards.py    # Клавіатури
│   └── my_db.sql       # SQLite база даних
└── users_data.xlsx     # Експортовані дані (генерується)
```

## Команди бота

### Користувацькі
- `/start` - Запуск бота, створення таблиці
- `📝 Додати подію` - Додати нову подію
- `🧺 Видалити подію` - Видалити подію за ID
- `🔍 Пошук події` - Пошук за ключовим словом
- `🧺 Видалити всю таблицю` - Видалити всі події

### Перегляд подій
- `today` - Події на сьогодні
- `tomorrow` - Події на завтра
- `this_month` - Події за цей місяць
- `next_month` - Події на наступний місяць
- `all_events` - Всі події (з пагінацією)

### Адмін-панель
- `🔑 Увійти як адмін` - Вхід в адмін-панель
- `📊 Статистика` - Статистика користувачів
- `👥 Список користувачів` - Список ID користувачів
- `📤 Експорт в Excel` - Експорт даних
- `🚪 Вийти` - Вихід з адмін-панелі

## Оптимізації та покращення

### Безпека
- ✅ Змінні оточення через `.env` (python-dotenv)
- ✅ Параметризовані SQL-запити (захист від SQL-ін'єкцій)
- ✅ Валідація імен таблиць
- ✅ Context managers для БД

### Архітектура
- ✅ Модульна структура (database, handlers, functions)
- ✅ Centralized database connection management
- ✅ Pathlib для роботи з шляхами
- ✅ Timezone support (Europe/Kyiv)

### Код
- ✅ Видалено дублювання хендлерів
- ✅ Прибрано закоментований код
- ✅ Додано логування
- ✅ Типізація та docstrings

## Вимоги

- Python 3.9+
- aiogram 3.x
- APScheduler
- pandas + openpyxl (для Excel)
- rapidfuzz (для нечіткого пошуку)
- pytz (для таймзон)

## Ліцензія

MIT
