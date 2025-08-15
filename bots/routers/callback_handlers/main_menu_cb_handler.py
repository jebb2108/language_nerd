import logging
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from utils.filters import IsBotFilter # noqa
from config import LOG_CONFIG, BOT_TOKEN_MAIN # noqa
from translations import QUESTIONARY, BUTTONS # noqa
from keyboards.inline_keyboards import get_on_main_menu_keyboard, get_go_back_keyboard # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='main_menu_cb_handler')

router = Router(name=__name__)


@router.callback_query(F.data == "about", IsBotFilter(BOT_TOKEN_MAIN))
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """
    await callback.answer()  # убираем "часики" на кнопке

    data = await state.get_data()
    lang_code = data.get("lang_code")

    msg = QUESTIONARY["about"][lang_code]

    # Редактируем текущее сообщение
    await callback.message.edit_text(
        text=msg,
        reply_markup=get_go_back_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    

@router.callback_query(F.data == "go_back", IsBotFilter(BOT_TOKEN_MAIN))
async def go_back(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()

    data = await state.get_data()
    user_id = data.get("user_id")
    first_name = data.get("first_name")
    lang_code = data.get("lang_code")
    msg = (
        f"{BUTTONS['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{QUESTIONARY['welcome'][lang_code]}"
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )
