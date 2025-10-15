from datetime import timedelta

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bot.translations import MESSAGES
from app.bot.utils.access_data import data_storage as ds
from app.dependencies import get_redis_client, get_yookassa
from exc import StorageDataException
from logging_config import opt_logger as log

logger = log.setup_logger('payment_cb_handler')

router = Router(name=__name__)

@router.callback_query()
async def subscription_expired_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    user_id = callback.from_user.id
    redis_client = await get_redis_client()
    yookassa_client = await get_yookassa()

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        link = await yookassa_client.create_monthly_payment_link(user_id)
        sent = await callback.message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )

        await redis_client.setex(f'user_payment:{user_id}', timedelta(minutes=10), sent.message_id)

    except StorageDataException:
        return logger.error(f"User {user_id} trying to acces data but doesn`t exist in DB")

    except Exception as e:
        return logger.error(f"Error in subscription_expired_handler: {e}")
