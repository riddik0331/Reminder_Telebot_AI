# Google Drive Backup Setup

## Як налаштувати бекап на Google Drive

### 1. Створи проект у Google Cloud Console

1. Перейди на [console.cloud.google.com](https://console.cloud.google.com/)
2. Натисни "Select Project" → "New Project"
3. Назви проект, наприклад "Reminder Bot Backup"
4. Натисни "Create"

### 2. Увімкни Google Drive API

1. У меню зліва вибери "APIs & Services" → "Library"
2. Знайди "Google Drive API"
3. Натисни на нього → "Enable"

### 3. Створи OAuth 2.0 credentials

1. Перейди в "APIs & Services" → "Credentials"
2. Натисни "Create Credentials" → "OAuth client ID"
3. Для "Application type" вибери "Desktop app"
4. Натисни "Create"
5. Скачай файл credentials.json

### 4. Помісти файл у папку з ботом

Поклади `credentials.json` в корінь проекту:
```
Reminder_Telebot_AI/
├── credentials.json  ← сюди
├── run.py
├── app/
└── ...
```

### 5. Запусти бота та авторизуйся

1. Запусти бота: `python run.py`
2. Увійди в адмін-панель
3. Натисни "☁️ Бекап на Google Drive"
4. Відкриється браузер для авторизації Google
5. Дозволь доступ
6. Файл `token.json` буде створено автоматично

### 6. Готово!

Тепер бекапи будуть зберігатися у папці "ReminderBot Backups" на твоєму Google Drive.

---

## Структура файлів

- `credentials.json` — OAuth credentials від Google Cloud Console (НЕ коммітити в git!)
- `token.json` — збережений токен авторизації (створюється автоматично)

## Troubleshooting

### "invalid_client: The OAuth client was not found"

Переконайся, що створив credentials для "Desktop app", а не "Web application".

### "Error 401: invalid_client"

Видали старий `token.json` і авторизуйся знову.

### "This app isn't verified"

При першому запуску Google попросить підтвердження. Можна натиснути "Advanced" → "Go to [project] (unsafe)".
