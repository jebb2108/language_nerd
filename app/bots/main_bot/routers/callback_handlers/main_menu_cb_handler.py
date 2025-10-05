import uuid
from datetime import datetime, timedelta

from aiogram.filters import and_f
from yookassa import Payment

from app.models import NewPayment
from config import config
from logging_config import opt_logger as log
from aiogram import F, Router
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.dependencies import get_db, get_rabbitmq
from app.bots.main_bot.utils.paytime import paytime
from app.bots.main_bot.translations import MESSAGES
from app.bots.main_bot.utils.access_data import data_storage
from app.bots.main_bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_go_back_keyboard, get_payment_keyboard,
)

logger = log.setup_logger("main_menu_cb_handler", config.LOG_LEVEL)

router = Router(name=__name__)


@router.callback_query(
    and_f(F.data == "about", paytime)
)
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """
    await callback.answer()  # убираем "часики" на кнопке
    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    msg = MESSAGES["about"][lang_code]

    # Редактируем текущее сообщение
    await callback.message.edit_caption(
        caption=msg,
        reply_markup=get_go_back_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(
    and_f(F.data == "go_back", paytime)
)
async def go_back(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()
    database = await get_db()
    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    msg = f"{MESSAGES['welcome'][lang_code]}"

    if not await database.check_profile_exists(user_id):
        msg += MESSAGES["get_to_know"][lang_code]
    else:
        msg += MESSAGES["pin_me"][lang_code]

    await callback.message.edit_caption(
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )

@router.callback_query(not paytime)
async def subscription_expired_handler(callback: CallbackQuery, state: FSMContext):

    user_id = callback.from_user.id
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
