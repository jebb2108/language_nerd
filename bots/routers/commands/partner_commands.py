import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from filters import IsBotFilter # noqa

from config import BOT_TOKEN_PARTNER # noqa

router = Router(name=__name__)
# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))

@router.message(Command("start"), IsBotFilter(BOT_TOKEN_PARTNER))
async def start(message: Message):
    await message.answer("Привет, я бот-партнер.\n"
                         "Примерное ожидание партнера составляет 3 минуты.\n"
                         "По всем вопросам обращайтесь к @user_bot6426")

@router.message(IsBotFilter(BOT_TOKEN_PARTNER))
async def echo(message: Message):
    if message.text:
        await message.copy_to(message.chat.id)
