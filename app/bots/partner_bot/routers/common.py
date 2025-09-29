from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.translations import MESSAGES
from app.bots.partner_bot.utils.access_data import data_storage

router = Router(name=__name__)


@router.message()
async def get_help_handler(message: Message, state: FSMContext, database: ResourcesMiddleware):
    data = await data_storage.get_storage_data(message.from_user.id, state, database)
    lang_code = data.get("lang_code")
    await message.bot.send_message(
        chat_id=message.chat.id, text=MESSAGES["get_help"][lang_code]
    )
