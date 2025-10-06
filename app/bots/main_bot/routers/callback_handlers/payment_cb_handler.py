import uuid
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from yookassa import Payment

from app.bots.main_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.main_bot.main import logger
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage as ds
from app.bots.main_bot.utils.exc import StorageDataException
from app.dependencies import get_rabbitmq
from app.models import NewPayment
from config import config


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
        logger.error(f"User {user_id} trying to acces data but doesn`t exist in DB")

    except Exception as e:
        logger.error(f"Error in subscription_expired_handler: {e}")


@router.callback_query(lambda callback: callback.message.content_type == ContentType.WEB_APP_DATA)
async def handle_payment(callback: CallbackQuery):
    """ Обработка платежа """
    user_id = callback.from_user.id
    payment_id = callback.message.web_app_data.data  # Пример получения ID платежа
    payment = Payment.find_one(payment_id)
    if payment.status == "succeeded":
        rabbit = await get_rabbitmq()
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
