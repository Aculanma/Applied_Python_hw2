from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()

# Состояния для логирования еды
class FoodLog(StatesGroup):
    food_weight = State()