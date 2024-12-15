import os
import asyncio
import random
import aiohttp
import logging

import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from datetime import datetime, timedelta
from aiogram import Router
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from cachetools import TTLCache


# Загрузка переменных из .env
load_dotenv()

# Получение API токенов
TOKEN = os.getenv("TELEGRAM_TOKEN")
THE_CAT_API_KEY = os.getenv("THE_CAT_API_KEY")
NASA_API_KEY = os.getenv("NASA_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Бот запущен.")


# Создание бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создание роутера для хендлеров (обработчиков)
router = Router()

# Создание клавиатуры с кнопками
# keyboard_builder = ReplyKeyboardBuilder()
# keyboard_builder.row(KeyboardButton(text="/joke"))
# keyboard_builder.row(KeyboardButton(text="/cat"))
# keyboard_builder.row(KeyboardButton(text="/nasa"))
# keyboard_builder.row(KeyboardButton(text="/dog"))
# keyboard_builder.row(KeyboardButton(text="/chuck_norris"))
# keyboard_builder.row(KeyboardButton(text="/weather"))
#
# keyboard = keyboard_builder.as_markup(resize_keyboard=True)

# Функция для установки команд меню
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="help", description="Помощь по использованию бота"),
        BotCommand(command="joke", description="Произвольная шутка"),
        BotCommand(command="cat", description="Произвольное фото кота"),
        BotCommand(command="nasa", description="Произвольное изображение из космоса"),
        BotCommand(command="dog", description="Произвольное фото кота"),
        BotCommand(command="chuck_norris", description="Факт о Чаке Норрисе"),
        BotCommand(command="weather", description="Погода в выбранном городе")
    ]
    await bot.set_my_commands(commands)

# Функция для перевода текста на русский
def translate_to_russian(text):
    try:
        translation = GoogleTranslator(source='auto', target='ru').translate(text)
        return translation
    except Exception as e:
        return f"Ошибка перевода: {e}"

# Асинхронная функция для получения случайной шутки
async def get_random_joke():
    url = "https://v2.jokeapi.dev/joke/Any"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                joke_data = await response.json()
                if joke_data['type'] == 'single':
                    return joke_data['joke']
                else:
                    return f"{joke_data['setup']} - {joke_data['delivery']}"
    except Exception as e:
        return f"Не удалось получить шутку: {e}"

# Асинхронная функция для получения случайного изображения кота
async def get_random_cat():
    url = "https://api.thecatapi.com/v1/images/search"
    headers = {"x-api-key": THE_CAT_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                return data[0]['url']
    except Exception as e:
        return f"Не удалось получить изображение кота: {e}"

# Асинхронная функция для получения случайного космического изображения
async def get_random_nasa_image():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    random_date = start_date + (end_date - start_date) * random.random()
    date_str = random_date.strftime("%Y-%m-%d")

    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={date_str}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data['url'], data['title']
    except Exception as e:
        return f"Не удалось получить изображение NASA: {e}", ""

# Асинхронная функция для получения случайного изображения собаки
async def get_random_dog():
    url = "https://dog.ceo/api/breeds/image/random"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                dog_data = await response.json()
                return dog_data['message']  # URL изображения
    except Exception as e:
        return f"Не удалось получить изображение собаки: {e}"

# Асинхронная функция для получения случайного факта о Чаке Норрисе
async def get_chuck_norris_fact():
    url = "https://api.chucknorris.io/jokes/random"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                fact_data = await response.json()
                return fact_data['value']  # Текст шутки
    except Exception as e:
        return f"Не удалось получить факт о Чаке Норрисе: {e}"

# Кеш для городов (на 10 минут)
weather_cache = TTLCache(maxsize=100, ttl=600)

# Словарь для перевода погодных условий
weather_descriptions = {
    "clear sky": "Ясное небо",
    "few clouds": "Малооблачно",
    "scattered clouds": "Рассеянные облака",
    "broken clouds": "Переменная облачность",
    "shower rain": "Ливневый дождь",
    "rain": "Дождь",
    "thunderstorm": "Гроза",
    "snow": "Снег",
    "mist": "Туман",
}

# Определяем состояния
class WeatherStates(StatesGroup):
    waiting_for_city_name = State()

# Асинхронная функция для получения текущей погоды
# async def get_weather(city):
#     api_key = OPENWEATHER_API_KEY
#     url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url) as response:
#                 weather_data = await response.json()
#                 if weather_data.get('cod') != 200:
#                     return f"Не удалось найти город: {city}"
#                 temp = weather_data['main']['temp']
#                 description = weather_data['weather'][0]['description']
#                 return f"В {city} сейчас {temp}°C, {description}."
#     except Exception as e:
#         return f"Не удалось получить погоду: {e}"

# Функция для перевода погодных условий
def translate_description(description):
    description = description.lower()
    return weather_descriptions.get(description, description.capitalize())


# Обработка текстового сообщения с названием города
@dp.message(WeatherStates.waiting_for_city_name)
async def get_weather_by_city(message: types.Message, state: FSMContext):
    city_name = message.text.strip().lower()  # Приведение города к нижнему регистру и удаление лишних пробелов
    logger.info(f"Запрос погоды для города: {city_name} от пользователя {message.from_user.id}")

    # Проверка на наличие данных в кеше
    if city_name in weather_cache:
        logger.info(f"Возвращаем закешированные данные для города: {city_name}")
        await message.answer(weather_cache[city_name])
        return

    try:
        # Установим тайм-аут для запроса в 20 секунд
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        logger.info(f"Отправка запроса к OpenWeatherMap для города: {city_name}")
        response = requests.get(url, timeout=20)  # Тайм-аут 20 секунд

        if response.status_code == 200:
            data = response.json()
            temp = data['main']['temp']
            temp1 = data['main']['humidity']
            pressure_gpa = data['main']['pressure']
            pressure_mm_hg = convert_gpa_to_mm_hg(pressure_gpa)
            description = data['weather'][0]['description']
            description_ru = translate_description(description)  # Перевод описания погоды_
            weather_info = (f"*Погода в городе {city_name.title()}:*\n*{description_ru}*, "
                            f"температура: *{temp}°C*, \nвлажность воздуха: *{temp1} %*,\nатмосферное давление : *{pressure_mm_hg:.2f} мм рт. ст.*")
            weather_cache[city_name] = weather_info
            await message.answer(weather_info, parse_mode="Markdown")
        else:
            await message.answer(f'{message.from_user.first_name}! Не удалось получить данные о погоде. Пожалуйста, проверьте название города*'
                                 , parse_mode="Markdown")
            # Устанавливаем состояние ожидания названия города
            await state.set_state(WeatherStates.waiting_for_city_name)
        # Завершаем состояние
        await state.clear()
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе погоды: {e}")
        await message.answer("Произошла ошибка при получении данных о погоде. Попробуйте позже.")


def convert_gpa_to_mm_hg(pressure_gpa):
    # Коэффициент для перевода из гПа в мм рт. ст.
    conversion_factor = 0.75006
    # Перевод давления
    pressure_mm_hg = pressure_gpa * conversion_factor
    return pressure_mm_hg

# Команда /start
@router.message(Command("start"))
async def start(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Вот что я могу:\n"
                         "*/joke* - Произвольная шутка\n"
                         "*/cat* - Произвольное фото кота\n"
                         "*/nasa* - Произвольное космическое изображение\n"
                         "*/dog* - Произвольное фото собаки\n"
                         "*/chuck_norris* - Случайный факт о Чаке Норрисе\n"
                         "*/weather* - Погода в выбранном городе\n"
                         "*/help* - Помощь по использованию бота", parse_mode="Markdown")

# Команда /help
@router.message(Command("help"))
async def help(message: Message):
    await message.answer("*Перечень функций бота:*\n"
                         "*/joke* - Произвольная шутка\n"
                         "*/cat* - Произвольное фото кота\n"
                         "*/nasa* - Произвольное космическое изображение\n"
                         "*/dog* - Произвольное фото собаки\n"
                         "*/chuck_norris* - Случайный факт о Чаке Норрисе\n"
                         "*/weather* - Погода в выбранном городе\n"
                         "*/help* - Помощь по использованию бота", parse_mode="Markdown")

# Команда /joke для получения и перевода шутки
@router.message(Command("joke"))
async def send_joke(message: Message):
    joke = await get_random_joke()  # Получаем шутку на английском
    translated_joke = translate_to_russian(joke)  # Переводим шутку на русский
    await message.answer(translated_joke)  # Отправляем переведённую шутку

# Команда /cat для получения фото кота
@router.message(Command("cat"))
async def send_cat(message: Message):
    cat_image_url = await get_random_cat()  # Получаем случайное изображение кота
    await message.answer_photo(photo=cat_image_url)  # Отправляем изображение

# Команда /nasa для получения космического изображения
@router.message(Command("nasa"))
async def send_nasa_image(message: Message):
    photo_url, title = await get_random_nasa_image()  # Получаем изображение и заголовок
    await message.answer_photo(photo=photo_url, caption=title)  # Отправляем изображение и заголовок

# Команда /dog для получения случайного изображения собаки
@router.message(Command("dog"))
async def send_dog(message: Message):
    dog_image_url = await get_random_dog()  # Получаем случайное изображение собаки
    await message.answer_photo(photo=dog_image_url)  # Отправляем изображение

# Команда /chuck для получения случайного факта о Чаке Норрисе с переводом
@router.message(Command("chuck_norris"))
async def send_chuck_norris_fact(message: Message):
    chuck_fact = await get_chuck_norris_fact()  # Получаем случайный факт о Чаке Норрисе на английском
    translated_fact = translate_to_russian(chuck_fact)  # Переводим факт на русский
    await message.answer(translated_fact)  # Отправляем переведённый факт

# Команда /weather для получения погоды
# @router.message(Command("weather"))
# async def send_weather(message: Message):
#     # Разделяем текст сообщения и получаем аргументы
#     args = message.text.split(maxsplit=1)
#     if len(args) < 2:
#         await message.answer("Пожалуйста, укажите город. Например: /weather Москва", reply_markup=keyboard)
#         return
#
#     city = args[1]  # Получаем название города
#     weather_info = await get_weather(city)
#     await message.answer(weather_info, reply_markup=keyboard)


@dp.message(Command("weather"))
async def start_weather_command(message: types.Message, state: FSMContext):
    await message.answer(
        f'*{message.from_user.first_name}!\nНапиши название города, чтобы узнать погоду*',
        parse_mode="Markdown")
    # Устанавливаем состояние ожидания названия города
    await state.set_state(WeatherStates.waiting_for_city_name)

# Регистрация роутера в диспетчере
dp.include_router(router)

# Запуск бота
async def main():
    dp.startup.register(set_commands)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())