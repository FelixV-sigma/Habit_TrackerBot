from aiogram.fsm.state import State, StatesGroup

class AddHabit(StatesGroup):
    name = State()

class DeleteHabit(StatesGroup):
    choose = State()

class DoneHabit(StatesGroup):
    choose = State()

class ReminderFSM(StatesGroup):
    waiting_for_time = State()
    waiting_for_days = State()