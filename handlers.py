from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery 
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Info, WaterLogForm, WorkoutLogForm 
from datetime import datetime 
import aiohttp
import urllib.parse
import base64
from config import OPENWEATHER_API_KEY
import matplotlib.pyplot as plt
import io
from aiogram.types import BufferedInputFile


"""
Модуль обработчиков (handlers) команд TelegramBot, включающий в себя: 

- Настройку профиля (/set_profile)
- Логирование воды (/log_water)
- Логирование еды через OpenFoodFacts API (/log_food)
- Логирование тренировок с кнопками (/log_workout)
- Просмотр прогресса (/check_progress)
- Графики прогресса (/graph)

Данные хранятся в памяти (словарь users), без базы данных.
"""

# Создаем словарь для хранения данных пользователей 
users = {} 

# Создаем роутеры для регистрации handlers 
router = Router()


# === Обработчик команды /start === 
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Я ваш HealthyBot.\nВведите /help для списка команд.")    


# === Обработчик команды /help ===
@router.message(Command("help"))
async def cmd_help(message: Message):
    commands = [
        "/start - Начало работы",
        "/set_profile - Настроить профиль (вес, рост, возраст, активность, город)",
        "/log_water - Записать выпитую воду (в мл)",
        "/log_food - Записать съеденную еду",
        "/log_workout - Записать тренировку (тип и длительность в минутах)",
        "/check_progress - Просмотреть прогресс (вода, калории, баланс)",
        "/help - Показать этот список команд",
        "/graph - Показать графики прогресса по воде и калориям"
    ]
    await message.reply("Доступные команды:\n" + "\n".join(commands))


# === Обработчик команды /set_profile === 
# Настройка профиля реализована как FSM диалог с пользователем 
@router.message(Command("set_profile"))
async def info_form(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):") 
    await state.set_state(Info.weight) 

@router.message(Info.weight)
async def process_weight(message: Message, state: FSMContext):
    await state.update_data(weight=float(message.text)) 
    await message.reply("Введите ваш рост (в см):")
    await state.set_state(Info.height)

@router.message(Info.height)
async def process_height(message: Message, state: FSMContext): 
    await state.update_data(height=float(message.text)) 
    await message.reply("Введите ваш возраст:") 
    await state.set_state(Info.age) 

@router.message(Info.age) 
async def process_age(message:Message, state: FSMContext): 
    await state.update_data(age=int(message.text)) 
    await message.reply("Сколько минут активности у вас в день?") 
    await state.set_state(Info.activity) 

@router.message(Info.activity) 
async def process_activity(message:Message, state:FSMContext): 
    await state.update_data(activity=int(message.text)) 
    await message.reply("В каком городе вы находитесь?") 
    await state.set_state(Info.location) 

async def get_weather(city: str) -> bool:
    """
    Получает текущую температуру в городе через OpenWeatherMap API.
    
    Возвращает True, если температура > 25°C (жаркая погода).
    """
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                temp = data["main"]["temp"]
                return temp > 25
    return False


@router.message(Info.location) 
async def process_location(message:Message, state:FSMContext):
    """
    Рассчитывает норму воды и калорий, иницилизирует профиль пользователя 
    
    Логика расчета нормы воды:
    30 мл на каждый 1 кг веса + 300 мл за каждые 30 минут активности (базово, без учета тренировки) + 500 мл за жаркую погоду (>25°C) 
    
    Логика расчета нормы калорий:
    10 ккал за каждый 1 кг веса + 6,15 ккал за каждый 1 см роста - 5 * возраст
    
    (данная формула является базовой и не учитывает тренировку,
    итоговый калораж (с учетом тренировки) будет посчитан после работы обработчика /log_workout
    и результат будет учтен в /check_process) 
    
    """
    await state.update_data(location=message.text) 
    data = await state.get_data()
    
    user_id = message.from_user.id
    
    # Расчёт норм воды
    def water_goal(weight: float, activity: int, hot_weather: bool=False) -> int:
        water_base = weight * 30
        base_activity = (activity //30) * 300
        base_weather = 500 if hot_weather else 0
        return int(water_base + base_activity + base_weather)
    
    # Расчет базовой нормы калорий 
    def calorie_goal(weight: float, height: float, age: int) -> int:
        calorie_base = 10 * weight + 6.25 * height - 5 * age
        return int(calorie_base)
    
    weight = data["weight"]
    height = data["height"]
    age = data["age"]
    activity = data["activity"]
    
    city = message.text.strip()
    hot_weather = await get_weather(city)
    
    water = water_goal(weight, activity, hot_weather) 
    calorie = calorie_goal(weight, height, age) 
    
    # Инициализация профиля пользовтеля 
    users[user_id] = {
        "weight": weight,
        "height": height,
        "age": age,
        "activity":activity,
        "location":city, 
        "total_water":water,
        "total_calories": calorie,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0,
        "hot_weather": hot_weather
    }
    
    await message.reply(
        f"Ваша норма воды: {water} мл\n"
        f"Ваша норма калорий: {calorie} ккал"
    ) 
    # Выходим из сценария настройки профиля пользователя, данные сохранены в словарь 
    await state.clear() 
    

# === Обработчик команды /log_water === 
# Отслеживание прогресса по количеству выпитой воды также реализуется через FSM диалог с пользователем 
@router.message(Command("log_water"))
# Запрашиваем у пользователя количество выпитой воды 
async def log_water_start(message: Message, state: FSMContext):
    await state.set_state(WaterLogForm.amount)
    await message.reply("Сколько воды вы выпили (в мл)?")

@router.message(WaterLogForm.amount)
# Сохраняем количество выпитой воды и отслеживаем как прогресс 
async def process_water_amount(message: Message, state: FSMContext):

    amount = int(message.text)
    
    user_id = message.from_user.id 
    
    total_water = users[user_id]["total_water"] 
    logged_water = users[user_id]["logged_water"] 
    new_logged_water = logged_water + amount

    
    users[user_id]["logged_water"] = new_logged_water 

    remaining = total_water - new_logged_water
    if remaining < 0:
        remaining = 0 
    
    await message.reply(
        f"Принято {amount} мл воды.\n" 
        f"Всего выпито: {new_logged_water} мл из {total_water} мл.\n"
        f"Осталось: {remaining} мл."
    )
    await state.clear()
    

# === Логирование еды /log_food === 
async def search_food(query: str):
    """Поиск продукта в OpenFoodFacts API
    Возвращает словарь с названием и калориями на 100 г
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={encoded_query}&json=1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                products = data.get("products", [])
                if products:
                    product = products[0]
                    calories = product.get("nutriments", {}).get("energy-kcal_100g", 0)
                    name = product.get("product_name", "Неизвестный продукт")
                    return {
                        "name": name,
                        "calories_per_100g": calories
                    }
            else:
                print(f"Ошибка API: {response.status}")
    return None


# === Обработчик команды /log_food === 
@router.message(Command("log_food"))
async def log_food_start(message: Message, state: FSMContext):
    """
    Запускает FSM-диалог для логирования еды.
    
    Логика:
    1. Пользователь вводит название продукта.
    2. Бот делает запрос к OpenFoodFacts API.
    3. Если продукт найден — запрашивает количество грамм.
    4. Рассчитывает калории и сохраняет в профиль пользователя.
    """
    await message.reply("Введите название продукта:")
    await state.set_state("food_search")

# Продолжение обработчика /log_food в конце, посколкьу при текущем расположении он перехватывает работу хэндлера /log_workout


# === Обработчик команды /log_workout === 

# Словарь: тип тренировки → коэффициент (ккал/мин) для учета вклада типа тренировки (йога - поменьше калорий сжигается при тренировке (4), при кроссфите побольше)
WORKOUTS = [
    ("Бег", 10),
    ("Ходьба", 5),
    ("Плавание", 8),
    ("Йога", 4),
    ("Велосипед", 8),
    ("Танцы", 7),
    ("Фитнес", 7),
    ("Силовая", 9),
    ("Кардио", 9),
    ("Прыжки", 10),
    ("Скалолазание", 9),
    ("Гребля", 8),
    ("Бокс", 10),
    ("Кроссфит", 10),
    ("Пилатес", 5),
    ("Растяжка", 3),
    ("Теннис", 7),
    ("Баскетбол", 8),
    ("Футбол", 8),
    ("Лыжи", 9),
] 

@router.message(Command("log_workout"))
async def log_workout_start(message: Message, state: FSMContext):
    """
    Показывает кнопки с типами тренировок из словаря WORKOUTS.
    
    Пользователь выбирает тренировку через нажатие кнопки и далее указывает длительность.
    
    Как работают кнопки:
    - Каждая кнопка имеет callback_data в формате "workout_{индекс}"
    - При нажатии на кнопку бот получает callback-запрос
    - Callback-запрос обрабатывается в @router.callback_query(lambda c: c.data.startswith("workout_"))
    """ 
    buttons = []
    for i in range(0, len(WORKOUTS), 2):
        row = []
        row.append(InlineKeyboardButton(text=WORKOUTS[i][0], callback_data=f"workout_{i}"))
        if i + 1 < len(WORKOUTS):
            row.append(InlineKeyboardButton(text=WORKOUTS[i+1][0], callback_data=f"workout_{i+1}"))
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.reply("Выберите тип тренировки:", reply_markup=keyboard)
    await state.set_state(WorkoutLogForm.type)
  
#@router.callback_query(lambda c: c.data.startswith("workout_")) в конце файла, потому что он перехватывает работу обработчика /check_progress (причину не нашла)
    
@router.message(WorkoutLogForm.duration)
async def process_workout_duration(message: Message, state: FSMContext):
    """
    Рассчитывает сожженные калории и дополнительную воду.
    
    Формулы:
    - Калории = длительность * коэффициент
    - Доп. вода = (длительность // 30) * 200 мл
    
    Пример:
    - Бег 30 мин → 300 ккал, +200 мл воды.
    """
    try:
        duration = int(message.text)
        
        data = await state.get_data()
        workout_type = data["workout_type"]
        coeff = data["workout_coeff"]
        
        calories_burned = duration * coeff
        additional_water = (duration // 30) * 200
        
        user_id = message.from_user.id
        if user_id not in users:
            users[user_id] = {"burned_calories": 0, "logged_water": 0}
        
        users[user_id]["burned_calories"] = users[user_id].get("burned_calories", 0) + calories_burned
        users[user_id]["logged_water"] = users[user_id].get("logged_water", 0) + additional_water
        
        await message.reply(
            f"{workout_type} {duration} мин → {calories_burned} ккал.\n"
            f"Рекомендуется дополнительно выпить {additional_water} мл воды."
        )
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число.")


# === Обработчик команды /check_progress === 

@router.message(Command("check_progress"))
async def check_progress(message: Message, state: FSMContext):
    """
    Показывает текущий прогресс по воде и калориям
    
    Логика:
    1. Проверяет, есть ли профиль у пользователя
    2. Получает данные из users[user_id]
    3. Рассчитывает:
       - Вода: выпито, осталось
       - Калории: базовая норма, сожжено, потреблено, баланс
    4. Формирует сообщение с прогрессом и отправляет пользователю
    
    Пример вывода:
    Прогресс:
    
    Вода:
     - Выпито: 1500 мл из 2400 мл
     - Осталось: 900 мл
    
    Калории:
     - Базовая норма: 2500 ккал
     - Сожжено: 400 ккал
     - Итоговая норма (с учётом тренировок): 2900 ккал
     - Потреблено: 1800 ккал
     - Баланс: 1400 ккал
    """
    user_id = message.from_user.id
    
    if user_id not in users:
        await message.reply("Сначала настройте профиль командой /set_profile")
        return

    data = users[user_id]
    
    # Вода
    total_water = data["total_water"]
    logged_water = data["logged_water"]
    remaining_water = max(0, total_water - logged_water)
    
    # Калории
    base_calories = data["total_calories"]
    logged_calories = data["logged_calories"]
    burned_calories = data["burned_calories"]
    updated_total_calories = base_calories + burned_calories 
    balance = logged_calories - burned_calories
    
    # Формируем сообщение
    progress_message = (
        "Прогресс:\n\n"
        "Вода:\n"
        f" - Выпито: {logged_water} мл из {total_water} мл.\n"
        f" - Осталось: {remaining_water} мл.\n\n"
        "Калории:\n"
        f" - Базовая норма: {base_calories} ккал.\n"
        f" - Сожжено: {burned_calories} ккал.\n" 
        f" - Итоговая норма (с учетом тренировок): {updated_total_calories} ккал.\n" 
        f" - Потреблено: {logged_calories} ккал.\n"
        f" - Баланс: {balance} ккал."
    )
    
    await message.reply(progress_message)


# === Обработчик команды /graph === 
    """
    Отправляет график прогресса по воде и калориям.
    
    Логика:
    1. Проверяет, есть ли профиль у пользователя.
    2. Получает данные из users[user_id].
    3. Создаёт два графика (вода и калории) с помощью matplotlib.
    4. Сохраняет график в буфер (BytesIO).
    5. Отправляет изображение пользователю.
    
    Графики:
    - Вода: столбчатая диаграмма с "Выпито" и "Осталось".
    - Калории: столбчатая диаграмма с "Потреблено" и "Сожжено".
    
    Пример вывода:
    [Изображение с двумя графиками]
    """
@router.message(Command("graph"))
async def send_graph(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сначала настройте профиль командой /set_profile")
        return

    data = users[user_id]
    logged_water = data["logged_water"]
    total_water = data["total_water"]
    logged_calories = data["logged_calories"]
    burned_calories = data["burned_calories"]

    # Создаем график
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))

    # График воды
    ax[0].bar(["Выпито", "Осталось"], [logged_water, total_water - logged_water], color=['blue', 'lightblue'])
    ax[0].set_title("Вода")
    ax[0].set_ylabel("мл")

    # График калорий
    ax[1].bar(["Потреблено", "Сожжено"], [logged_calories, burned_calories], color=['green', 'red'])
    ax[1].set_title("Калории")
    ax[1].set_ylabel("ккал")

    plt.tight_layout()

    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Отправляем изображение
    photo = BufferedInputFile(buf.getvalue(), filename="progress.png") 
    await message.reply_photo(photo) 

    # Закрываем график
    plt.close(fig)

# Продолжение обработчика /log_food (перенесен вниз, так как при серединном расположении перехватывает работу обработчика /log_workout)
@router.message(lambda message: True)
async def handle_food_input(message: Message, state: FSMContext):
    """
    Обрабатывает ввод названия продукта и количества грамм.
    
    Должен быть в самом конце файла, чтобы не перехватывать команды.
    """
    current_state = await state.get_state()

    if current_state == "food_search":
        product = await search_food(message.text)
        if product:
            await message.reply(
                f"Найден продукт: {product['name']}\n"
                f"Калорий на 100 г: {product['calories_per_100g']} ккал\n"
                f"Введите количество грамм:"
            )
            await state.update_data(
                food_name=product["name"],
                calories_per_100g=product["calories_per_100g"]
            )
            await state.set_state("food_amount")
        else:
            await message.reply("Продукт не найден. Попробуйте другое название.")
            await state.clear()

    elif current_state == "food_amount":
        try:
            grams = int(message.text)
            data = await state.get_data()
            calories = int(data["calories_per_100g"] * grams / 100)
            
            user_id = message.from_user.id
            if user_id not in users:
                users[user_id] = {"logged_calories": 0}
            users[user_id]["logged_calories"] = users[user_id].get("logged_calories", 0) + calories
            
            await message.reply(f"Вы записали {grams} г {data['food_name']}.\n"
                               f"Это {calories} ккал.")
            await state.clear()
        except ValueError:
            await message.reply("Пожалуйста, введите корректное число.")


# Продолжение обработчика /log_workout 
@router.callback_query(lambda c: c.data.startswith("workout_"))
async def handle_workout_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор тренировки через кнопку.
    
    Сохраняет тип и коэффициент, запрашивает длительность.
    
    Как работает:
    - Бот получает callback-запрос с data="workout_{индекс}"
    - Извлекает индекс и находит соответствующую тренировку в списке WORKOUTS
    - Сохраняет данные в FSM-состоянии
    - Отправляет сообщение с подтверждением выбора
    """
    index = int(callback.data.split("_")[1])
    workout_name, coeff = WORKOUTS[index]
    
    await state.update_data(workout_type=workout_name, workout_coeff=coeff)
    await callback.message.edit_text(f"Вы выбрали: {workout_name}")
    await callback.message.answer("Введите длительность тренировки (в минутах):")
    await state.set_state(WorkoutLogForm.duration)
    await callback.answer()  


#Функция для подключения обработчиков
def setup_handlers(dp):
    dp.include_router(router)
