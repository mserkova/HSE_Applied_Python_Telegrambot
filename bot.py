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



# === ВЕБ-СЕРВЕР ДЛЯ RENDER ===
from aiohttp import web

async def health_check(request):
    """Эндпоинт для проверки работоспособности."""
    return web.Response(text="OK")

async def start_web_server():
    """Запускает веб-сервер на порту из переменной окружения."""
    app = web.Application()
    app.router.add_get("/", health_check)
    port = int(os.getenv("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер запущен на порту {port}")


if __name__ == "__main__":
    import os
    # Запускаем бота и веб-сервер одновременно
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_until_complete(start_web_server())
    loop.run_forever()























