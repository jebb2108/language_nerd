import uuid
from datetime import timedelta, datetime

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType
from yookassa import Payment

from app.bots.main_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage as ds
from app.bots.main_bot.filters.paytime import paytime
from app.bots.partner_bot.utils.exc import StorageDataException
from app.dependencies import get_redis_client, get_db
from app.models import NewPayment
from logging_config import opt_logger as log
from config import config

logger = log.setup_logger('common')

router = Router(name=__name__)

@router.message(paytime)
async def get_help_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        await message.bot.send_message(
            chat_id=message.chat.id, text=MESSAGES["get_help"][lang_code]
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in get_help_handler: {e}")


@router.message()
async def pay_cmd(message: Message, state: FSMContext):
    if not await paytime(message.from_user.id): return

    user_id = message.from_user.id
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
        await message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in pay_cmd handler: {e}")
