import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import config, LOG_CONFIG
from app.bots.main_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.main_bot.keyboards.inline_keyboards import get_on_main_menu_keyboard
from app.bots.main_bot.utils.access_data import data_storage
from app.bots.main_bot.translations import MESSAGES

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="menu_commands")

# Инициализируем роутер
router = Router(name=__name__)


@router.message(Command("menu", prefix="!/"))
async def show_main_menu(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):

    # Получаем данные из состояния
    data = await data_storage.get_storage_data(message.from_user.id, state, database)
    user_id = data.get("user_id")
    first_name = data.get("first_name")
    lang_code = data.get("lang_code")

    msg = (
        f"{MESSAGES['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{MESSAGES['welcome'][lang_code]}"
    )

    await message.answer(
        text=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )
