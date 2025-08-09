from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN_PARTNER # noqa
from middlewares.rate_limit_middleware import RateLimitMiddleware, RateLimitInfo # noqa
from utils.filters import IsBotFilter # noqa

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))


@router.message(Command("start"), IsBotFilter(BOT_TOKEN_PARTNER))
async def start(message: Message):
    await message.answer(
        "Привет, я бот-партнер.\n"
        "Примерное ожидание партнера составляет 3 минуты.\n"
        "По всем вопросам обращайтесь к @user_bot6426"
    )

@router.message(IsBotFilter(BOT_TOKEN_PARTNER))
async def echo(message: Message, rate_limit_info: RateLimitMiddleware):
    if message.text:
        await message.copy_to(message.chat.id)
    count = rate_limit_info.message_count
    first_message = rate_limit_info.last_message_time
    await message.reply(
        text=f"Your message: {message.text}\n"
        f"Rate limit info: {count} messages at {first_message}"
    )
