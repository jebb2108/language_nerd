import uuid
from datetime import timedelta

from yookassa import Payment, Configuration
from aiogram import Router

from aiogram.filters import Command, and_f
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from app.bots.main_bot.filters.paytime import paytime
from app.bots.main_bot.utils.exc import StorageDataException
from app.dependencies import get_db, get_redis_client
from config import config
from app.bots.main_bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_payment_keyboard,
)
from app.bots.main_bot.utils.access_data import data_storage as ds
from app.bots.main_bot.translations import MESSAGES
from logging_config import opt_logger as log

logger = log.setup_logger("main menu commands", config.LOG_LEVEL)

# Инициализируем роутер
router = Router(name=__name__)

Configuration.account_id = config.YOOKASSA_SHOP_ID
Configuration.secret_key = config.YOOKASSA_SECRET_KEY

@router.message(
    and_f(Command("menu", prefix="!/"), paytime)
)
async def show_main_menu(message: Message, state: FSMContext):

    # Получаем данные из состояния
    database = await get_db()
    user_id = message.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    msg = f"{MESSAGES['welcome'][lang_code]}"
    if not await database.check_profile_exists(user_id):
        msg += MESSAGES["get_to_know"][lang_code]
    else:
        msg += MESSAGES["pin_me"][lang_code]

    image_from_file = FSInputFile(config.ABS_PATH_TO_IMG_ONE)
    await message.answer_photo(
        photo=image_from_file,
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )