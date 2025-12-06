from datetime import timedelta

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.dependencies import get_gateway
from src.exc import StorageDataException
from src.keyboards.inline_keyboards import get_payment_keyboard
from src.logconf import opt_logger as log
from src.translations import MESSAGES
from src.utils.access_data import data_storage as ds

logger = log.setup_logger('payment_cb_handler')

router = Router(name=__name__)

@router.callback_query()
async def subscription_expired_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    user_id = callback.from_user.id

    gateway = await get_gateway()
    async with gateway() as session:
        link = await session.get('yookassa_link', user_id)

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        sent = await callback.message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )


    except StorageDataException:
        await callback.message.answer("You`re not registered. Press /start to do so")
        return logger.error(f"User {user_id} trying to acces data but doesn`t exist in DB")

    except Exception as e:
        return logger.error(f"Error in subscription_expired_handler: {e}")
