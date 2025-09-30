import logging
import uuid

from yookassa import Payment
from aiogram import Router

from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, ContentType

from app.bots.main_bot.utils.paytime import paytime
from app.dependencies import get_db
from config import config, LOG_CONFIG
from app.bots.main_bot.keyboards.inline_keyboards import get_on_main_menu_keyboard, get_payment_keyboard
from app.bots.main_bot.utils.access_data import data_storage
from app.bots.main_bot.translations import MESSAGES

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="menu_commands")

# Инициализируем роутер
router = Router(name=__name__)


@router.message(Command("menu", prefix="!/"))
async def show_main_menu(message: Message, state: FSMContext):

    # Получаем данные из состояния
    database = await get_db()
    data = await data_storage.get_storage_data(message.from_user.id, state)
    user_id = data.get("user_id")
    lang_code = data.get("lang_code")

    msg = f"{MESSAGES['welcome'][lang_code]}"
    if not await database.check_profile_exists(user_id):
        msg += MESSAGES['get_to_know'][lang_code]
    else:
        msg += MESSAGES['pin_me'][lang_code]

    image_from_file = FSInputFile(config.ABS_PATH_TO_IMG_ONE)
    await message.answer_photo(
        photo=image_from_file,
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )


@router.message(
    Command("pay", prefix="!/"),
    lambda message: paytime(message.from_user.id)
)
async def pay_cmd(message: Message, state: FSMContext):

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

    if payment.status == "succeeded":
        await message.answer("Платеж прошел успешно!")
    else:
        await message.answer("Ошибка оплаты.")
