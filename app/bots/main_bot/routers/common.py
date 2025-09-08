from aiogram import Router
from aiogram.types import Message

router = Router(name=__name__)


@router.message()
async def echo(message: Message):
    if message.text:
        await message.copy_to(message.chat.id)
    else:
        await message.bot.send_message(
            chat_id=message.chat.id, text="press /help to get help"
        )
