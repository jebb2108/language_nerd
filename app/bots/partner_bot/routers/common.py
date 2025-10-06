import uuid
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType
from yookassa import Payment

from app.bots.partner_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.partner_bot.filters.paytime import paytime
from app.bots.partner_bot.translations import MESSAGES
from app.bots.partner_bot.utils.access_data import data_storage
from app.bots.partner_bot.utils.exc import StorageDataException
from app.dependencies import get_db, get_redis_client
from app.models import NewPayment
from logging_config import opt_logger as log
from config import config

logger = log.setup_logger('common')

router = Router(name=__name__)


@router.message(paytime)
async def get_help_handler(message: Message, state: FSMContext):
    data = await data_storage.get_storage_data(message.from_user.id, state)
    lang_code = data.get("lang_code")
    await message.bot.send_message(
        chat_id=message.chat.id, text=MESSAGES["get_help"][lang_code]
    )

@router.message()
async def subscription_expiration_handler(message: Message, state: FSMContext):
    if not await paytime(message.from_user.id): return

    user_id = message.from_user.id
    try:
        data = await data_storage.get_storage_data(user_id, state)
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
            "description": "Оплата подписки"
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

    except Exception as e:
        logger.error(f"Error in subscription_expiration_handler: {e}")


@router.message(lambda message: message.content_type == ContentType.WEB_APP_DATA)
async def handle_payment(message: Message):
    payment_id = message.web_app_data.data
    payment = Payment.find_one(payment_id)
    user_id = message.from_user.id
    if payment.status == "succeeded":

        database = await get_db()
        redis_client = await get_redis_client()
        new_untill = datetime.now(tz=config.TZINFO) + timedelta(days=31)

        await redis_client.delete(f"user_paid:{user_id}")
        new_payment = NewPayment(
            user_id=user_id,
            period=config.MONTH,
            amount=199,
            currency="RUB",
            trial=False,
            untill=new_untill.isoformat(),
        )
        await database.create_payment(**new_payment.model_dump())
        await message.answer("Платеж прошел успешно!")
    else:
        await message.answer("Ошибка оплаты.")


