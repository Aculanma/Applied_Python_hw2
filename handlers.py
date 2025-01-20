from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Form
from states import FoodLog
import requests
#from config import NUTRITION_ID
#from config import NUTRITION_TOKEN


router = Router()

# Словарь для хранения данных пользователей
users = {}

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Я ваш бот.")

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"        
        "/start - Начало работы\n"
        "/set_profile - Настройка профиля\n"
        "/log_water - Логирование воды в мл.\n"
        "/log_food - Логирование еды\n"    
        "/check_progress - Прогресс по воде и калориям"
        )
# Делаю команду /set_profile
@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)

@router.message(Form.weight)
async def get_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id] = {"weight": float(message.text)}
    await message.reply("Введите ваш рост (в см):")
    await state.set_state(Form.height)

@router.message(Form.height)
async def get_height(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["height"] = float(message.text)
    await message.reply("Введите ваш возраст:")
    await state.set_state(Form.age)

@router.message(Form.age)
async def get_age(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["age"] = int(message.text)
    await message.reply("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)

@router.message(Form.activity)
async def get_activity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["activity"] = int(message.text)
    await message.reply("В каком городе вы находитесь?")
    await state.set_state(Form.city)

@router.message(Form.city)
async def get_city(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["city"] = message.text
    weight = users[user_id]["weight"]
    height = users[user_id]["height"]
    age = users[user_id]["age"]
    activity = users[user_id]["activity"]
    # Расчет нормы воды
    users[user_id]["water_goal"] = weight * 30 + (activity // 30) * 500
    # Расчет нормы калорий
    users[user_id]["calorie_goal"] = 10 * weight + 6.25 * height - 5 * age
    await message.reply(
        f"Профиль настроен!\nНорма воды составляет: {users[user_id]['water_goal']} мл.\n"
        f"Норма калорий составляет: {users[user_id]['calorie_goal']} ккал."
    )
    await state.clear()

# Делаю команду /log_water
@router.message(Command("log_water"))
async def cmd_log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Для выполнения данной команды необходимо сперва настроить профиль с помощью /set_profile")
        return
    try:
        amount = int(message.text.split()[1])
        users[user_id]["log_water"] = users[user_id].get("log_water", 0) + amount
        water_goal = users[user_id]["water_goal"]
        await message.reply(
            f'Выпито: {users[user_id]["log_water"]} мл. из {water_goal} мл.\n'
            f'Осталось: {water_goal - users[user_id]["log_water"]} мл.'
        )
    except:
        await message.reply("Используйте команду: /log_water <количество>, например /log_water 500")

# Функция для получения информации о продукте
def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:  # Проверяем, есть ли найденные продукты
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        return None
    print(f"Ошибка: {response.status_code}")
    return None

# Делаю команду /log_food
@router.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Для выполнения данной команды необходимо сперва настроить профиль с помощью /set_profile")
        return
    try:
        product_name = message.text.split()[1]
    except:
        await message.reply("Используйте команду: /log_food <название продукта>, например /log_food banan")
        return

    # Получаем информацию о продукте
    product_info = get_food_info(product_name)
    if product_info:
        name = product_info['name']
        calories_100g = product_info['calories']
        await message.reply(f"{name} — {calories_100g:.1f} ккал. на 100 г. Сколько грамм вы съели?")
        await state.update_data(food_name=name, calories_per_100g=calories_100g)
        await state.set_state(FoodLog.food_weight)
    else:
        await message.reply("Не удалось найти информацию о продукте. Попробуйте снова.")

@router.message(FoodLog.food_weight)
async def process_food_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        weight = float(message.text)
        data = await state.get_data()
        name = data["food_name"]
        calories_100g = data["calories_per_100g"]

        # Расчет калорий
        calories = (calories_100g / 100) * weight
        users[user_id]["log_calories"] = users[user_id].get("log_calories", 0) + calories
        await message.reply(f"Записано: {calories:.1f} ккал.")
        await state.clear()
    except:
        await message.reply("Попробуйте еще раз. Введите число, например, 100")

# Делаю команду /log_workout
@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Для выполнения данной команды необходимо сперва настроить профиль с помощью /set_profile")
        return
    try:
        _, workout_type, time_training = message.text.split()
        time_min = int(time_training)
    except (ValueError, IndexError):
        await message.reply("Используйте команду: /log_workout <тип тренировки> <время (мин)>, например: /log_workout бег 30")
        return
    # Расчёт калорий
    calories_per_min = 15  # Возьмем значение для средней интенсивности
    burned_calories = calories_per_min * time_min
    # Расчет доп. объема воды
    additional_water = (time_min // 30) * 200  # 200 мл. воды за каждые 30 минут тренировки
    users[user_id]["log_water"] = users[user_id].get("log_water", 0) + additional_water
    users[user_id]["burned_calories"] = users[user_id].get("burned_calories", 0) + burned_calories

    await message.reply(
        f"{workout_type.capitalize()} {time_min} минут — {burned_calories} ккал. "
        f"Дополнительно: выпейте {additional_water} мл. воды."
    )

# Делаю команду /check_progress
@router.message(Command("check_progress"))
async def cmd_check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Для выполнения данной команды необходимо сперва настроить профиль с помощью /set_profile")
        return
    # Отберем данные по конкретному пользователю
    user_data = users[user_id]
    # Извлечем данные пользователя
    water_goal = user_data.get("water_goal", 0)
    log_water = user_data.get("log_water", 0)
    remaining_water = max(0, water_goal - log_water)
    calorie_goal = user_data.get("calorie_goal", 0)
    log_calories = user_data.get("log_calories", 0)
    burned_calories = user_data.get("burned_calories", 0)
    calorie_balance = log_calories - burned_calories
    # Вывод прогресса
    progress_text = (
        f"Прогресс:\n"
        f"Вода:\n"
        f"- Выпито: {log_water} мл. из {water_goal} мл.\n"
        f"- Осталось: {remaining_water} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {log_calories} ккал. из {calorie_goal} ккал.\n"
        f"- Сожжено: {burned_calories} ккал.\n"
        f"- Баланс: {calorie_balance} ккал."
    )
    await message.reply(progress_text)