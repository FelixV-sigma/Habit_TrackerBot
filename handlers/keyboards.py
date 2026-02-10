from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def habits_keyboard(habits, action: str):
    buttons = []
    for habit in habits:
        buttons.append([
            InlineKeyboardButton(
                text=f"{habit['name']}",
                callback_data=f"{action}:{habit['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_delete_keyboard(habit_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да",
                    callback_data=f"confirm_delete:{habit_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data="cancel_delete"
                )
            ]
        ]
    )

def reminder_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Вкл", callback_data="reminder_on"),
                InlineKeyboardButton(text="❌ Выкл", callback_data="reminder_off")
            ]
        ]
    )

def reminder_days_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Каждый день", callback_data="days_all")],
            [
                InlineKeyboardButton(text="Пн–Пт", callback_data="days_weekdays"),
                InlineKeyboardButton(text="Сб–Вс", callback_data="days_weekend"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="days_cancel")]
        ]
    )


