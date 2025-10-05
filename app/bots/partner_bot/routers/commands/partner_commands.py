import uuid
from datetime import datetime, timedelta
from typing import Union

import aiohttp
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, and_f
from aiogram.enums import ParseMode, ContentType
from yookassa import Payment

from app.bots.main_bot.utils.paytime import paytime
from app.bots.partner_bot.keyboards.inline_keyboards import show_topic_keyboard, get_payment_keyboard
from app.dependencies import get_db, get_redis_client, get_rabbitmq
from app.models import UserMatchRequest, NewPayment
from config import config
from app.bots.partner_bot.translations import MESSAGES, TRANSCRIPTIONS

from app.bots.partner_bot.keyboards.inline_keyboards import (
    show_partner_menu_keyboard,
    get_search_keyboard,
)

from app.bots.partner_bot.utils.access_data import data_storage
from logging_config import opt_logger as log

# Инициализируем роутер
router = Router(name=__name__)

logger = log.setup_logger("partner_commands", config.LOG_LEVEL)


@router.message(and_f(Command("menu", prefix="!/"), paytime))
async def show_main_menu(message: Message, state: FSMContext):
    """Главное меню бота"""
    database = await get_db()
    user_id = message.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    nickname = data.get("nickname", None)
    language = data.get("language")
    lang_code = data.get("lang_code")

    if not await database.check_user_exists(user_id):
        await message.answer(text="I can`t seem to know you :( Go to @lllangbot")
        return

    elif nickname is None:
        await message.answer(
            text=MESSAGES["not_registered"][lang_code],
            parse_mode=ParseMode.HTML,
        )
        return

    greeting = MESSAGES["hello"][language] + " <b>" + nickname + "</b>!"
    intro = MESSAGES["full_intro"][lang_code]
    await state.update_data(
        user_id=user_id,
        lang_code=lang_code,
        first_name=message.from_user.first_name,
    )

    image_from_file = FSInputFile(config.ABS_PATH_TO_IMG_TWO)
    await message.answer_photo(
        photo=image_from_file,
        caption=greeting + "\n\n" + intro,
        reply_markup=show_partner_menu_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )


@router.message(and_f(Command("location", prefix="!/"), paytime))
async def get_my_location(message: Message, state: FSMContext):
    """Обработчик команды /location"""

    database = await get_db()
    user_id = message.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    result = await database.get_users_location(user_id)
    if not result or result["latitude"] is None:
        await message.answer(text=MESSAGES["no_location"][lang_code])
        return

    city = result["city"]
    country = result["country"]

    msg = MESSAGES["your_location"][lang_code]
    await message.answer(
        text=f"{msg}: <b>{city}</b>, <b>{country}</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(and_f(Command("change_topic", prefix="!/"), paytime))
async def change_topic(message: Message):
    user_id = message.from_user.id
    database = await get_db()
    user_info = await database.get_user_info(user_id)
    lang_code = user_info.get("lang_code")
    topic = user_info.get("topic")
    msg = MESSAGES["current_topic"][lang_code].format(
        topic=TRANSCRIPTIONS["topics"][topic][lang_code]
    )
    await message.answer(
        text=msg, reply_markup=show_topic_keyboard(lang_code), parse_mode=ParseMode.HTML
    )


@router.message(and_f(Command("new_session", prefix="!/"), paytime))
async def new_session_handler(
    message: Union[Message, CallbackQuery], state: FSMContext
):
    """Обработчик команды /new_session - запускает поиск партнера"""

    database = await get_db()
    redis_client = await get_redis_client()

    data = await data_storage.get_storage_data(message.from_user.id, state, database)
    user_id = data.get("user_id")
    username = data.get("username")
    language = data.get("language")
    fluency = data.get("fluency")
    dating = str(data.get("dating"))
    gender = data.get("gender") or "unknown"
    topic = data.get("topic")
    lang_code = data.get("lang_code")

    if username == "NO USERNAME":
        msg = MESSAGES["no_username"][lang_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return

    if not await database.check_profile_exists(user_id):
        await message.answer(
            text=MESSAGES["not_registered"][lang_code],
            parse_mode=ParseMode.HTML,
        )
        return

    # Отменяем предыдущий поиск, если он был
    is_searching = await redis_client.get(f"searching:{user_id}")
    if is_searching:
        return logger.info(f"Уже существует поиск для пользователя {user_id}")

    await redis_client.setex(f"searching:{user_id}", 150, username)
    logger.debug(f"Создана сессия поиска для пользователя {user_id}")

    await message.answer(
        text=MESSAGES["search_began"][lang_code],
        parse_mode=ParseMode.HTML,
        reply_markup=get_search_keyboard(lang_code),
    )

    # Отправляю запрос на сервер
    url = "{DOMAIN}/api/match".format(
        DOMAIN=f"{config.BASE_URL}:{config.CHAT_SERVER_PORT}"
    )
    headers = {"Content-Type": "application/json"}
    payload = UserMatchRequest(
        user_id=user_id,
        username=username,
        gender=gender,
        criteria={
            "language": language,
            "fluency": fluency,
            "dating": dating,
            "topic": topic,
        },
        lang_code=lang_code,
    )

    logger.info(f"Отправка запроса на: {url}")
    logger.debug(f"Данные запроса: {payload}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=url, json=payload.model_dump(), headers=headers
            ) as response:
                response_text = await response.text()
                logger.warning(f"Статус ответа: {response.status}")
                logger.warning(f"Тело ответа: {response_text}")

                if response.status != 200:
                    logger.error(
                        f"Ошибка при запросе к API: {response.status}. Ответ: {response_text}"
                    )
                else:
                    logger.info("Запрос успешно обработан")

    except Exception as e:
        logger.error(f"Исключение при выполнении запроса: {e}")




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
