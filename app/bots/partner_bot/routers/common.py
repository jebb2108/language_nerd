from aiogram import Router
from aiogram.types import Message
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitInfo
from app.bots.partner_bot.utils.filters import IsBotFilter
from config import config

router = Router(name=__name__)


@router.message(IsBotFilter(config.BOT_TOKEN_PARTNER))
async def echo(message: Message, rate_limit_info: RateLimitInfo):
    # Убираем кнопки после любого сообщения
    count = rate_limit_info.message_count
    first_message = rate_limit_info.last_message_time
    await message.reply(
        text=f"Your message: {message.text}\n"
        f"Rate limit info: {count} messages at {first_message}",
    )
