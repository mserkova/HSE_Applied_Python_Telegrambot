import asyncio
from aiogram import Bot,Dispatcher
from config import TOKEN, OPENWEATHER_API_KEY
from handlers import setup_handlers
from middlewares import LoggingMiddleware
from aiogram.fsm.storage.memory import MemoryStorage 

#Создаем экземпляры бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage() #Хранение состояний FSM 
dp = Dispatcher(storage=storage) 

#Настраиваем middleware для логирования входящих сообщений и callback-запросы (нажатия на кнопки)
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())

#Настраиваем обработчики 
setup_handlers(dp)

#Функция запуска бота 
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 