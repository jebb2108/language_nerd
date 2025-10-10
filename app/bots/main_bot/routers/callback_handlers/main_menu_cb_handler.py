from aiogram.filters import and_f

from app.bots.main_bot.utils.exc import StorageDataException
from config import config
from logging_config import opt_logger as log
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.dependencies import get_db
from app.bots.main_bot.filters.paytime import paytime
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage as ds
from app.bots.main_bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_go_back_keyboard, )

logger = log.setup_logger("main_menu_cb_handler", config.LOG_LEVEL)

router = Router(name=__name__)

@router.callback_query(and_f(F.data == "sub_details", paytime))
async def manage_subscription_handler(callback: CallbackQuery):
    await callback.answer()
    pass


@router.callback_query(
    and_f(F.data == "about", paytime)
)
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """

    await callback.answer()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        msg = MESSAGES["about"][lang_code]

        # Редактируем текущее сообщение
        await callback.message.edit_caption(
            caption=msg,
            reply_markup=get_go_back_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data, but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in about handler: {e}")


@router.callback_query(
    and_f(F.data == "go_back", paytime)
)
async def go_back(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()
    database = await get_db()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        msg = f"{MESSAGES['welcome'][lang_code]}"

        if not await database.check_profile_exists(user_id):
            msg += MESSAGES["get_to_know"][lang_code]
        else:
            msg += MESSAGES["pin_me"][lang_code]

        await callback.message.edit_caption(
            caption=msg,
            reply_markup=get_on_main_menu_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data, but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in go_back handler: {e}")



