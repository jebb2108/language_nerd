import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from translations import BUTTONS, QUESTIONARY # noqa
from utils.filters import IsBotFilter # noqa
from config import BOT_TOKEN_MAIN, LOG_CONFIG # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa
from keyboards.inline_keyboards import get_on_main_menu_keyboard, get_go_back_keyboard # noqa

from utils.access_data_from_storage import get_storage_data # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='menu_commands')

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену основного бота
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))


@router.message(Command("menu", prefix='!/'), IsBotFilter(BOT_TOKEN_MAIN))
async def show_main_menu(message: Message, state: FSMContext, database: ResourcesMiddleware):

    # Получаем данные из состояния
    data = await get_storage_data(message, state, database)
    user_id = data.get("user_id")
    first_name = data.get("first_name")
    lang_code = data.get("lang_code")

    msg = (
        f"{BUTTONS['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{QUESTIONARY['welcome'][lang_code]}"
    )

    await message.answer(
        text=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )

