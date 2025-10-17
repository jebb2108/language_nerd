from typing import Union

import aiohttp
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile

from app.bot.filters.approved import approved
from app.bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
)
from app.bot.middlewares.rate_limit_middleware import RateLimitInfo
from app.bot.translations import MESSAGES, TRANSCRIPTIONS
from app.bot.utils.access_data import data_storage as ds
from app.dependencies import get_db
from config import config
from logging_config import opt_logger as log

logger = log.setup_logger("main menu commands", config.LOG_LEVEL)

# Инициализируем роутер
router = Router(name=__name__)


class MultiSelection(StatesGroup):
    waiting_nickname = State()
    waiting_language = State()
    waiting_topic = State()
    waiting_intro = State()


@router.message(
    and_f(Command("menu", prefix="!/"), approved)
)
async def show_main_menu(message: Message, state: FSMContext, rate_limit_info: RateLimitInfo):

    logger.debug(
        f"User %s message count: %s",
        message.from_user.id, rate_limit_info.message_count
    )

    # Получаем данные из состояния
    user_id = message.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")
    is_active = data.get("is_active")
    if not is_active: return

    msg = f"{MESSAGES['welcome'][lang_code]}"
    if data.get("nickname", False):
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


@router.message(and_f(Command("location", prefix="!/"), approved))
async def get_my_location(message: Message, state: FSMContext):
    """Обработчик команды /location"""

    database = await get_db()
    user_id = message.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    result = await database.get_users_location(user_id)
    if not result or result["latitude"] is None:
        await message.answer(text=MESSAGES["no_location"][lang_code])
        return

    city = result["city"]
    country = result["country"]

    msg = MESSAGES["your_location"][lang_code]
    await message.answer(
        text=f"{msg}: <b>{city}</b>, <b>{country}</b>",
        parse_mode=ParseMode.HTML,
    )