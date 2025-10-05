import uuid
from datetime import timedelta, datetime

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType
from yookassa import Payment

from app.bots.main_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage
from app.bots.main_bot.utils.paytime import paytime
from app.dependencies import get_rabbitmq
from app.models import NewPayment
from config import config

router = Router(name=__name__)

@router.message(paytime)
async def get_help_handler(message: Message, state: FSMContext):
    data = await data_storage.get_storage_data(message.from_user.id, state)
    lang_code = data.get("lang_code")
    await message.bot.send_message(
        chat_id=message.chat.id, text=MESSAGES["get_help"][lang_code]
    )

@router.callback_query(not paytime)
@router.message(not paytime)
async def pay_cmd(message: Message, state: FSMContext):
    if not await paytime(message.from_user.id): return

    user_id = message.from_user.id
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

@router.message(lambda message: message.content_type == ContentType.WEB_APP_DATA)
async def handle_payment(message: Message):
    payment_id = message.web_app_data.data  # Пример получения ID платежа
    payment = Payment.find_one(payment_id)
    user_id = message.from_user.id
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
        await message.answer("Платеж прошел успешно!")
    else:
        await message.answer("Ошибка оплаты.")
