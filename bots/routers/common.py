from aiogram import Router
from aiogram.types import Message

from utils.filters import IsBotFilter # noqa
from config import BOT_TOKEN_MAIN # noqa

# Инициализируем роутер
router = Router(name=__name__)

@router.message(IsBotFilter(BOT_TOKEN_MAIN))
async def handle_other_messages(message: Message):
    """
    Обработчик всех остальных сообщений (не команд)
    Напоминает пользователю использовать /help
    """

    await message.answer("Используйте /help для получения списка команд")
