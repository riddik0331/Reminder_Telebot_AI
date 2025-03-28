import asyncio
import logging
import app.functions as f

from aiogram import Bot, Dispatcher

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger  # Импортируем CronTrigger

from app.handlers import router
from config import TELEBOT_TOKEN

bot = Bot(TELEBOT_TOKEN)
dp = Dispatcher()
# Подключаем к диспетчеру роутер
dp.include_router(router)

# Объявляем планировщик
scheduler = AsyncIOScheduler()

# Объявление основной функции
async def main():
    # dp.include_router(router) # или здесь)
    # Добавляем задачу к планировщику
    scheduler.add_job(
        f.send_daily_events,
        # "interval",
        # seconds=3,
        CronTrigger(hour=9, minute=0),  # Время выполнения: каждый день в 9:00
        kwargs={'bot': bot}
    )
    # Запускаем планировщик
    scheduler.start()
    # Запускаем бота
    await dp.start_polling(bot)

"""# Объявление основной функции
async def main():
    # dp.include_router(router) # или здесь)
    # Добавляем задачу к планировщику
    scheduler.add_job(send_daily_events, "interval", seconds=3)
    # Запускаем планировщик
    scheduler.start()
    # Запускаем бота
    await dp.start_polling(bot)



# Функция, которая будет отправлять события
async def send_daily_events():
    for user_id in await f.get_user_ids():
        events = await f.get_events_for_today(user_id)  # Эта функция должна вернуть список событий на сегодняшний день
        if events:
            await bot.send_message(user_id, events)
        else:
            await bot.send_message(user_id, "На сегодня нет событий.")
"""

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot interrupted by User')
