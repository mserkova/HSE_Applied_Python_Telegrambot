from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import traceback 
   
#Создаем класс для логирования входящих событий 
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        """
        Вызывается при каждом событии (сообщение или callback)

        Args: 
            handler: Функция-обработчик события
            event: Событие (Message или CallbackQuery)
            data: Дополнительные данные (например, FSM-состояние)

        Returns:
            Результат выполнения обработчика (handler) 
        """ 
        try:
            if isinstance(event, Message):
                print(f"Получено сообщение: {event.text}")
            elif isinstance(event, CallbackQuery):
                print(f"Получен callback: {event.data}")
            
            result = await handler(event, data)
            return result
            
        except Exception as e:
            print(f"Ошибка в middleware: {e}") 
            traceback.print_exc() 
            
