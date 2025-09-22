from aiogram import Router
from aiogram.types import Message
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitInfo

router = Router(name=__name__)


@router.message()
async def echo(message: Message, rate_limit_info: RateLimitInfo):
    count = rate_limit_info.message_count
    first_message = rate_limit_info.last_message_time
    await message.reply(
        text=f"Your message: {message.text}\n"
        f"Rate limit info: {count} messages at {first_message}",
    )
