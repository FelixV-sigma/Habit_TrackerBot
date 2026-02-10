from aiogram import Router
from aiogram.types import Message, BotCommand
from aiogram.filters import Command

router = Router()
@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "Приветствую тебя, мой дорогой пользователь!👋\n\n"
        "Я бот Habit Tracker - бот, предназначенный для трекинга привычек.\n"
    )
async def set_commands(bot):
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="add", description="Добавить привычку"),
        BotCommand(command="list", description="Список привычек"),
        BotCommand(command="cancel", description="Отменить выполнение привычки (но она останется в списке)"),
        BotCommand(command="delete", description="Удалить привычку"),
        BotCommand(command="done", description="Выполненн(ая/ые) привычк(а/и)"),
        BotCommand(command="stats", description="Статистика по привычкам"),
        BotCommand(command="week_stats", description="Статистика за 7 дней"),
        BotCommand(command="reminder", description="Управление напоминаниями")
    ]
    await bot.set_my_commands(commands)

@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Нужна помощь?\n\n"
        "/start - Начало работы бота Habit Tracker\n"
        "/help - Помощь\n"
    )