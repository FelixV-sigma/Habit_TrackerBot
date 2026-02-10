import logging

from anyio import current_time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from .. import database
from .. import logger

logger = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

async def send_reminders(bot):
    logger.info("Напоминания запущены")
    now = datetime.now()
    weekday = now.weekday()  # 0 = Пн, 6 = Вс

    users = await database.get_users_with_reminders()

    for user in users:
        days = user.get("reminder_days", "all")

        if days != "all":
            allowed_days = list(map(int, days.split(",")))
            if weekday not in allowed_days:
                continue

        habits = await database.get_user_habits(user["user_id"])
        if not habits:
            continue

        text = "⏰ Пора выполнить привычки!\n\n"
        for habit in habits:
            text += f"• {habit['name']}\n"

        await bot.send_message(
            user["user_id"],
            text,
            parse_mode="Markdown"
        )
