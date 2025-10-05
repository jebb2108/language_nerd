import uuid

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType
from yookassa import Payment

from app.bots.partner_bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bots.partner_bot.filters.paytime import paytime
from app.bots.partner_bot.translations import MESSAGES
from app.bots.partner_bot.utils.access_data import data_storage
from app.dependencies import get_db
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
    database = await get_db()
    if payment.status == "succeeded":
        await database.create_payment(user_id, config.MONTH, ..., ..., ..., ...)
        await message.answer("Платеж прошел успешно!")
    else:
        await message.answer("Ошибка оплаты.")

