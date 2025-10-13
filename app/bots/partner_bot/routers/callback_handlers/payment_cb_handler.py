from datetime import timedelta

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bots.partner_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.partner_bot.translations import MESSAGES
from app.bots.partner_bot.utils.access_data import data_storage
from exc import StorageDataException
from app.dependencies import get_redis_client, get_yookassa
from logging_config import opt_logger as log

logger = log.setup_logger('payment_cb_handler')

router = Router()

@router.callback_query()
async def subscription_expired_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    user_id = callback.from_user.id
    redis_client = await get_redis_client()
    yookassa_client = await get_yookassa()
    try:
        data = await data_storage.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        # Отправка ссылки на оплату
        link = await yookassa_client.create_monthly_payment_link(user_id)
        sent = await callback.message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )

        await redis_client.setex(
            f'user_payment:{user_id}', timedelta(minutes=10), sent.message_id
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        return await callback.message.answer("You`re not registered. Press /start to do so")
    except Exception as e:
        return logger.error(f"Error in subscription_expired_handler: {e}")