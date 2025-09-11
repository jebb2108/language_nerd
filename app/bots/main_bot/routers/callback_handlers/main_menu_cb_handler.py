import logging
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bots.main_bot.utils.filters import IsBotFilter
from app.bots.main_bot.middlewares.resources_middleware import ResourcesMiddleware
from config import LOG_CONFIG, config
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data_from_storage import get_storage_data
from app.bots.main_bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_go_back_keyboard,
)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="main_menu_cb_handler")

router = Router(name=__name__)


@router.callback_query(F.data == "about", IsBotFilter(config.BOT_TOKEN_MAIN))
async def about(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """
    await callback.answer()  # убираем "часики" на кнопке

    data = await get_storage_data(callback.message, state, database)
    lang_code = data.get("lang_code")

    msg = MESSAGES["about"][lang_code]

    # Редактируем текущее сообщение
    await callback.message.edit_text(
        text=msg,
        reply_markup=get_go_back_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "go_back", IsBotFilter(config.BOT_TOKEN_MAIN))
async def go_back(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()

    data = await get_storage_data(callback.message, state, database)
    user_id = data.get("user_id")
    first_name = data.get("first_name")
    lang_code = data.get("lang_code")
    msg = (
        f"{MESSAGES['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{MESSAGES['welcome'][lang_code]}"
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )
