"""Telegram Reminder Bot - Main entry point."""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.handlers import router
from app.database import (
    get_user_ids,
    get_events_for_today,
    get_events_with_reminders,
    get_events_for_date,
)
from app.ai_helper import ai
from config import TELEBOT_TOKEN, TIMEZONE, DEFAULT_REMINDER_DAYS

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Bot initialization
bot = Bot(token=TELEBOT_TOKEN)
dp = Dispatcher()

# Include router
dp.include_router(router)

# Scheduler initialization
scheduler = AsyncIOScheduler()


async def send_daily_events(bot: Bot):
    """
    Send daily event reminders to all users.
    Called by scheduler every day at 9:00 AM.
    """
    user_ids = await get_user_ids()

    for user_id in user_ids:
        try:
            events = await get_events_for_today(user_id)

            if events:
                await bot.send_message(
                    user_id,
                    f"📅 *Події на сьогодні:*\n\n{events}",
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(user_id, "📅 На сьогодні події відсутні.")
        except Exception as e:
            logging.error(f"Error sending daily reminder to user {user_id}: {e}")


async def send_reminder_notifications(bot: Bot):
    """
    Send reminder notifications N days before events.
    Called by scheduler every day at 8:00 AM.
    """
    now = datetime.now(TIMEZONE)
    today_md = now.strftime("%m-%d")
    current_month = now.strftime("%m")
    current_year = now.year

    # Get all active events
    events_data = await get_events_with_reminders()

    # Group by user_id
    user_events = {}
    for event_data in events_data:
        user_id = event_data[0]
        if user_id not in user_events:
            user_events[user_id] = []
        user_events[user_id].append(
            {
                "id": event_data[1],
                "date": event_data[2],
                "name": event_data[3],
                "reminder_days": [int(d) for d in event_data[4].split(",")]
                if event_data[4]
                else DEFAULT_REMINDER_DAYS,
                "category": event_data[5] if len(event_data) > 5 else "other",
            }
        )

    # Send reminders
    for user_id, events in user_events.items():
        try:
            for event in events:
                event_date_str = event["date"]
                event_md = event_date_str[5:]  # Get mm-dd from YYYY-mm-dd

                # Calculate days until event in current year
                this_year_event_date = datetime.strptime(
                    f"{current_year}-{event_md}", "%Y-%m-%d"
                ).date()
                days_until = (this_year_event_date - now.date()).days

                # If event passed this year, check next year
                if days_until < 0:
                    next_year_event_date = datetime.strptime(
                        f"{current_year + 1}-{event_md}", "%Y-%m-%d"
                    ).date()
                    days_until = (next_year_event_date - now.date()).days

                # Check if we need to send reminder
                if days_until > 0 and days_until in event["reminder_days"]:
                    # Try AI-generated message with category
                    message = await ai.generate_reminder_message(
                        event["name"], event["date"], days_until, event["category"]
                    )

                    if not message:
                        # Fallback
                        date_formatted = this_year_event_date.strftime("%d.%m.%Y")
                        message = f"⏰ Через {days_until} дней: {event['name']} ({date_formatted})"

                    await bot.send_message(
                        user_id,
                        f"🔔 *Нагадування:*\n\n{message}",
                        parse_mode="Markdown",
                    )
        except Exception as e:
            logging.error(f"Error sending reminder to user {user_id}: {e}")


async def main():
    """Main function to start the bot."""
    # Daily events at 9:00 AM
    scheduler.add_job(
        send_daily_events,
        CronTrigger(hour=9, minute=0, timezone=TIMEZONE),
        kwargs={"bot": bot},
        id="daily_events",
    )

    # Reminder notifications at 8:00 AM
    scheduler.add_job(
        send_reminder_notifications,
        CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
        kwargs={"bot": bot},
        id="reminder_notifications",
    )

    # Start scheduler
    scheduler.start()

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=BASE_DIR / "bot.log",
        filemode="a",
    )

    logging.info("Starting Telegram Reminder Bot...")

    try:
        # Windows fix: use selector event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
        print("Bot interrupted by User")
