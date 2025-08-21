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

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='menu_commands')

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену основного бота
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))


@router.message(Command("menu"), IsBotFilter(BOT_TOKEN_MAIN))
async def show_main_menu(message: Message, state: FSMContext, database: ResourcesMiddleware):

    await set_user_info(message, state, database)
    # Получаем данные из состояния
    data = await state.get_data()
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


async def set_user_info(message: Message, state: FSMContext, database: ResourcesMiddleware):
    await state.clear()
    user_id = message.from_user.id
    try:
        user_info = await database.get_user_info(user_id)
        username = user_info.get("username", message.from_user.username)
        first_name = user_info.get("first_name", message.from_user.first_name)
        lang_code = user_info.get("lang_code", message.from_user.language_code)
        await state.update_data(
            user_id=user_id,
            ussername=username,
            first_name=first_name,
            lang_code=lang_code,
        )

    except Exception as e:
        logger.error(f"Database error: {e}")

