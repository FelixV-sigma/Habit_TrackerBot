import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from Habit_TrackerBot.config import TOKEN
from Habit_TrackerBot import database
from Habit_TrackerBot.handlers import commands, habits
from Habit_TrackerBot.handlers.commands import set_commands
from Habit_TrackerBot.handlers.scheduler_bot import scheduler, send_reminders
from Habit_TrackerBot.logger import setup_logging


async def main():
    setup_logging()
    logging.info("Бот Habit Tracker запущен")

    await database.init_db()
    logging.info("База данных подключена")

    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    await set_commands(bot)
    logging.info("Команды бота установлены")

    dp.include_router(commands.router)
    dp.include_router(habits.router)

    scheduler.add_job(
        send_reminders,
        trigger="cron",
        minute="*",
        args=[bot]
    )
    scheduler.start()
    logging.info("Планировщик запущен ")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
