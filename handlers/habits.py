import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .states import AddHabit, DeleteHabit, DoneHabit, ReminderFSM
from .keyboards import habits_keyboard, confirm_delete_keyboard, reminder_keyboard
from datetime import date, timedelta, time
from .. import database
from .. import logger
import re

logger = logging.getLogger("habit")
router = Router()
@router.message(ReminderFSM.waiting_for_time)
async def set_time(message: Message, state: FSMContext):
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", message.text):
        await message.answer("❌ Неверный формат. Введите HH:MM")
        return

    hours, minutes = map(int, message.text.split(":"))
    reminder_time = time(hours, minutes)

    await state.update_data(reminder_time=reminder_time)

    await message.answer(
        "📅 Теперь выбери дни напоминаний:\n\n"
        "1️⃣ Каждый день\n"
        "2️⃣ Будни (Пн–Пт)\n"
        "3️⃣ Выходные (Сб–Вс)\n\n"
        "Напиши цифру:"
    )
    await state.set_state(ReminderFSM.waiting_for_days)

 
@router.message(ReminderFSM.waiting_for_days)
async def set_days(message: Message, state: FSMContext):
    days_map = {
        "1": "all",
        "2": "0,1,2,3,4",
        "3": "5,6"
    }

    if message.text not in days_map:
        await message.answer("❌ Введи 1, 2 или 3")
        return

    data = await state.get_data()
    reminder_time = data["reminder_time"]
    days = days_map[message.text]

    await database.set_reminder_with_time(
        message.from_user.id,
True,
        reminder_time
    )
    await database.set_reminder_schedule(
        message.from_user.id,
        days
    )

    await message.answer(
        "✅ Напоминания включены!\n\n"
        f"⏰ Время: {reminder_time}\n"
        f"📅 Дни: {message.text}"
    )
    await state.clear()

@router.message(Command("reminder"))
async def reminder_cmd(message: Message):
    settings = await database.get_user_settings(message.from_user.id)

    if settings:
        status = "включены" if settings["reminders_enabled"] else "выключены"
        time = settings["reminder_time"]
        text = f"⏰ Напоминания сейчас: *{status}*\nВремя: {time}"
    else:
        text = "⏰ Напоминания сейчас: *выключены*"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=reminder_keyboard()
    )

@router.callback_query(F.data == "reminder_on")
async def reminder_on(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🕒 Введите время напоминаний в формате HH:MM\nНапример: 08:30"
    )
    await state.set_state(ReminderFSM.waiting_for_time)
    await callback.answer()

@router.callback_query(F.data == "reminder_off")
async def reminder_off(callback: CallbackQuery):
    await database.set_reminder(callback.from_user.id, False)
    await callback.message.answer("🔕 Напоминания выключены")
    await callback.answer()

@router.message(Command("add"))
async def add_habit_start(message: Message, state: FSMContext):
    await state.set_state(AddHabit.name)
    await message.answer("Введите название привычки:")

@router.message(AddHabit.name)
async def add_habit_name(message: Message, state: FSMContext):
    habit_name = message.text.strip()

    logger.info(
        "User %s adding habit: %s",
        message.from_user.id,
        habit_name
    )

    if len(habit_name) < 2:
        await message.answer("Название слишком короткое. Попробуйте еще раз")
        return

    async with database.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO habits (user_id, name) VALUES ($1, $2)",
            message.from_user.id, habit_name
        )

    await state.clear()
    await message.answer(f"Привычка «{habit_name}» добавлена ✅")

@router.message(Command("list"))
async def list_habits(message: Message):
    habits = await database.get_user_habits(message.from_user.id)

    if not habits:
        await message.answer("У вас пока нет привычек")
        return

    text = "📋 *Твои привычки:*\n\n"
    for i, habit in enumerate(habits, start=1):
        text += (f"{i}. {habit['name']}\n"
            f"🔥 Серия: {habit['streak']} дней подряд\n"
            f"📊 Всего выполнено: {habit['count']}\n\n"
        )

    await message.answer(text, parse_mode="Markdown")

@router.message(Command("cancel"))
async def cancel_fsm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие привычки отменено")

@router.message(Command("done"))
async def done_habit(message: Message, state: FSMContext):
    async with database.pool.acquire() as conn:
        habits = await conn.fetch(
            "SELECT id, name FROM habits WHERE user_id = $1",
            message.from_user.id
        )

    if not habits:
        await message.answer("❌ У тебя нет привычек")
        return

    await state.set_state(DoneHabit.choose)
    await message.answer(
        "✅ Выбери привычку, которую выполнил:",
        reply_markup=habits_keyboard(habits, "done")
    )

@router.callback_query(lambda c: c.data.startswith("done:"))
async def done_habit_callback(callback: CallbackQuery, state: FSMContext):
    habit_id = int(callback.data.split(":")[1])
    today = date.today()

    logger.info(
        "User %s marked habit %s as done",
        callback.from_user.id,
        habit_id
    )

    async with database.pool.acquire() as conn:
        habit = await conn.fetchrow(
            "SELECT name, count, streak, last_done FROM habits WHERE id = $1",
            habit_id
        )

        if not habit:
            await callback.answer("Привычка не найдена", show_alert=True)
            return

        if habit["last_done"] == today:
            new_streak = habit["streak"]
        elif habit["last_done"] == today - timedelta(days=1):
            new_streak = habit["streak"] + 1
        else:
            new_streak = 1

        await conn.execute(
            "UPDATE habits SET count = count + 1, streak = $1, last_done = $2 WHERE id = $3",
            new_streak, today, habit_id
            )

        await state.clear()
        await callback.message.edit_text(
        f"✅ Привычка «{habit['name']}» выполнена!\n"
            f"🔥 Серия: {new_streak} дней подряд\n"
            f"📊 Всего выполнено: {habit['count'] + 1}",
            parse_mode="Markdown"
        )
        await callback.answer()

@router.message(Command("delete"))
async def delete_habit(message: Message, state: FSMContext):
    async with database.pool.acquire() as conn:
        habits = await conn.fetch(
            "SELECT id, name FROM habits WHERE user_id = $1",
            message.from_user.id
        )

    if not habits:
        await message.answer("❌ У тебя нет привычек")
        return

    await state.set_state(DeleteHabit.choose)
    await message.answer(
        "🗑 Выбери привычку для удаления:",
        reply_markup=habits_keyboard(habits, "delete")
    )

@router.callback_query(lambda c: c.data.startswith("delete:"))
async def delete_habit_ask_confirm(callback: CallbackQuery):
    habit_id = int(callback.data.split(":")[1])

    async with database.pool.acquire() as conn:
        habit = await conn.fetchrow(
            "SELECT name FROM habits WHERE id = $1",
            habit_id
        )

    if not habit:
        await callback.answer("Привычка уже удалена", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить привычку «{habit['name']}»?",
        reply_markup=confirm_delete_keyboard(habit_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("confirm_delete:"))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    habit_id = int(callback.data.split(":")[1])

    logger.warning(
        "User %s deleted habit %s",
        callback.from_user.id,
        habit_id
    )

    async with database.pool.acquire() as conn:
        habit = await conn.fetchrow(
            "SELECT name FROM habits WHERE id = $1",
            habit_id
        )

        if not habit:
            await callback.answer("Привычка уже удалена", show_alert=True)
            return

        await conn.execute(
            "DELETE FROM habits WHERE id = $1",
            habit_id
        )

    await state.clear()
    await callback.message.edit_text(
        f"🗑 Привычка «{habit['name']}» удалена"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено")
    await callback.answer()

@router.message(Command("stats"))
async def stats(message: Message):
    total, best_streak, top_habits, avg_streak = await database.get_stats(
        message.from_user.id
    )

    if total["habits"] == 0:
        await message.answer("У вас пока нет привычек для статистики")
        return

    text = (
        "📊 Статистика по привычкам\n\n"
        f"Всего привычек: {total['habits']}\n"
        f"Всего выполнений: {total['total_done']}\n\n"
    )

    if best_streak and best_streak["streak"] > 0:
        text += (
            "🔥 Лучшая серия:\n"
            f"{best_streak['name']} — {best_streak['streak']} дней\n\n"
        )

    if top_habits:
        text += "🏆 Топ по выполнению:\n"
        for i, habit in enumerate(top_habits, start=1):
            text += f"{i}. {habit['name']} — {habit['count']}\n"

    text += f"\n📈 Средняя серия: {avg_streak:.1f} дней"

    await message.answer(text, parse_mode="Markdown")

@router.message(Command("week_stats"))
async def week_stats(message: Message):
    week_done, top_week = await database.get_week_stats(
        message.from_user.id
    )

    if week_done == 0:
        await message.answer(
            "📅 За последние 7 дней выполнений не было.\n"
            "Самое время начать 💪"
        )
        return

    text = (
        "📅 *Статистика за 7 дней*\n\n"
        f"✅ Выполнено привычек: {week_done}\n\n"
    )

    if top_week:
        text += "🏆 *Топ за неделю:*\n"
        for i, habit in enumerate(top_week, start=1):
            text += f"{i}. {habit['name']} — {habit['cnt']} раз\n"

    await message.answer(text, parse_mode="Markdown")

@router.message(ReminderFSM.waiting_for_time)
async def reminder_fallback(message: Message):
    await message.answer(
        "❌ Я жду время в формате HH:MM\n"
        "Например: 08:30 или 21:45"
    )

@router.message(DoneHabit.choose)
async def done_fallback(message: Message):
    await message.answer(
        "❗️ Пожалуйста, нажми кнопку с привычкой"
    )

@router.message(DeleteHabit.choose)
async def delete_fallback(message: Message):
    await message.answer(
        "⚠️ Для удаления нажми кнопку с привычкой"
    )
