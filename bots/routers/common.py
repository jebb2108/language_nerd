from aiogram import Router
from aiogram.types import Message

from de_injection import ResourcesMiddleware, Resources # noqa


# Инициализируем ресурсы и роутер
resources = Resources()
router = Router(name=__name__)

# Регистрируем middleware на самом роутере
router.message.middleware(ResourcesMiddleware(resources))

@router.message()
async def handle_other_messages(message: Message, resources: Resources):
    """
    Обработчик всех остальных сообщений (не команд)
    Напоминает пользователю использовать /start
    """
    await message.answer("Используйте /start для получения меню")
