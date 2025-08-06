import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN_PARTNER  # noqa
from de_injection import ResourcesMiddleware, Resources  # noqa
from filters import IsBotFilter  # noqa

# Инициализируем ресурсы и роутер
resources = Resources()
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))

# Регистрируем middleware
router.message.middleware(ResourcesMiddleware(resources))
router.callback_query.middleware(ResourcesMiddleware(resources))


@router.message(Command("start"), IsBotFilter(BOT_TOKEN_PARTNER))
async def start(message: Message, resources: Resources):
    await message.answer(
        "Привет, я бот-партнер.\n"
        "Примерное ожидание партнера составляет 3 минуты.\n"
        "По всем вопросам обращайтесь к @user_bot6426"
    )


@router.message(IsBotFilter(BOT_TOKEN_PARTNER))
async def echo(message: Message, resources: Resources):
    if message.text:
        await message.copy_to(message.chat.id)
