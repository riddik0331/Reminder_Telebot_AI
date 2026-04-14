@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Telegram Reminder Bot
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Please create .env file with TELEBOT_TOKEN and ADMIN_PASSWORD
    echo You can copy .env.example and fill in your values
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting bot...
echo.

REM Run the bot
python run.py

REM Check exit code
if errorlevel 1 (
    echo.
    echo [ERROR] Bot crashed with error code %errorlevel%
    echo Check bot.log for details
    pause
)
