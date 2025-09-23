import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, FSInputFile

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
    lang_code = data.get("lang_code")

    msg = f"{MESSAGES['welcome'][lang_code]}"
    if not await database.check_profile_exists(user_id):
        msg += MESSAGES['get_to_know'][lang_code]

    image_from_file = FSInputFile("media/IMG_3903.PNG")
    await message.answer_photo(
        photo=image_from_file,
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )


