import uuid
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from yookassa import Payment

from app.bots.partner_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.partner_bot.main import logger
from app.bots.partner_bot.translations import MESSAGES
from app.bots.partner_bot.utils.access_data import data_storage
from app.bots.partner_bot.utils.exc import StorageDataException
from app.dependencies import get_rabbitmq
from app.models import NewPayment
from config import config

router = Router()

@router.callback_query()
async def subscription_expired_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    user_id = callback.from_user.id
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
        await callback.message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )
    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")
    except Exception as e:
        logger.error(f"Error in subscription_expired_handler: {e}")


@router.callback_query(lambda callback: callback.message.content_type == ContentType.WEB_APP_DATA)
async def handle_payment(callback: CallbackQuery):
    payment_id = callback.message.web_app_data.data  # Пример получения ID платежа
    payment = Payment.find_one(payment_id)
    user_id = callback.from_user.id
    rabbit = await get_rabbitmq()
    if payment.status == "succeeded":
        new_untill = datetime.now(tz=config.TZINFO) + timedelta(days=31)
        new_payment = NewPayment(
            user_id=user_id,
            period=config.MONTH,
            amount=199,
            currency="RUB",
            trial=False,
            untill=new_untill.isoformat(),
        )
        await rabbit.publish_payment(new_payment)
        await callback.message.answer("Платеж прошел успешно!")
    else:
        await callback.message.answer("Ошибка оплаты.")
