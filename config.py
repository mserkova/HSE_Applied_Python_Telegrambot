import os
from dotenv import load_dotenv 

# Загрузка переменных окружения из .env файла
load_dotenv()

# Чтение токена из переменной окружения 
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise ValueError("Переменная окружения OPENWEATHER_API_KEY не установлена") 