from aiogram import Router
from aiogram.types import Message

from bots.middlewares.rate_limit_middleware import RateLimitMiddleware

# Инициализируем роутер
router = Router(name=__name__)

@router.message()
async def handle_other_messages(message: Message):
    """
    Обработчик всех остальных сообщений (не команд)
    Напоминает пользователю использовать /start
    """

    await message.answer("Используйте /start для получения меню")
