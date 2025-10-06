import uuid
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from yookassa import Payment, Webhook

from app.bots.main_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage as ds
from app.bots.main_bot.utils.exc import StorageDataException
from app.dependencies import get_redis_client, get_db
from app.models import NewPayment
from logging_config import opt_logger as log
from config import config

logger = log.setup_logger('payment_cb_handler')

router = Router(name=__name__)

@router.callback_query()
async def subscription_expired_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)

        lang_code = data.get("lang_code")

        # Создание платежа в ЮKassa
        payment = Payment.create({
            "amount": {
                "value": "199.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/lllangbot"
            },
            "capture": True,
            "description": "Оплата подписки",
            "meta": {
                "user_id": user_id
            }
        }, uuid.uuid4())

        # Отправка ссылки на оплату
        link = payment.confirmation.confirmation_url
        await callback.message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data but doesn`t exist in DB")

    except Exception as e:
        logger.error(f"Error in subscription_expired_handler: {e}")
