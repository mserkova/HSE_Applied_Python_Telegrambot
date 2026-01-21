from aiogram.fsm.state import State, StatesGroup

"""
Модуль состояний/сценариев FSM: 

Содержит классы для управления состояниями при работе с:
- Настройкой профиля (Info)
- Логированием воды (WaterLogForm)
- Логированием тренировок (WorkoutLogForm)
"""

#Класс для сценария настройки профиля пользователя
class Info(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    location = State() 

#Класс для сценария логирования воды 
class WaterLogForm(StatesGroup):
    amount = State()

#Класс для сценария логирования тренировок
class WorkoutLogForm(StatesGroup):
    type = State()
    duration = State()
    
    
    