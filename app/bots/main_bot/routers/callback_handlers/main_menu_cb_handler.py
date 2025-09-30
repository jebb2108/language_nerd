import logging
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.dependencies import get_db
from config import LOG_CONFIG
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage
from app.bots.main_bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_go_back_keyboard,
)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="main_menu_cb_handler")

router = Router(name=__name__)


@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """
    await callback.answer()  # убираем "часики" на кнопке
    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    msg = MESSAGES["about"][lang_code]

    # Редактируем текущее сообщение
    await callback.message.edit_caption(
        caption=msg,
        reply_markup=get_go_back_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )



@router.callback_query(F.data == "go_back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()
    database = await get_db()
    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    msg = (
        f"{MESSAGES['welcome'][lang_code]}"
    )

    if not await database.check_profile_exists(user_id):
        msg += MESSAGES['get_to_know'][lang_code]
    else:
        msg += MESSAGES['pin_me'][lang_code]

    await callback.message.edit_caption(
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )