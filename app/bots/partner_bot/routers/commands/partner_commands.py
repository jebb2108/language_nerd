import logging
import os
import re

import asyncio
import json
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
from aiogram.enums import ParseMode

from config import config, LOG_CONFIG
from app.models import UserMatchRequest
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitInfo
from app.bots.main_bot.utils.filters import IsBotFilter
from app.bots.partner_bot.translations import MESSAGES, QUESTIONARY, BUTTONS

from app.bots.partner_bot.keyboards.inline_keyboards import (
    show_partner_menu_keyboard,
)
from app.bots.partner_bot.keyboards.regular_keyboards import (
    show_location_keyboard,
    show_dating_keyboard,
)

from app.bots.partner_bot.utils.access_data_from_storage import get_storage_data

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(config.BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(config.BOT_TOKEN_PARTNER))

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="partner_commands")


class PollingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_bday = State()
    waiting_for_intro = State()
    waiting_for_dating = State()
    waiting_for_location = State()


class SearchStates(StatesGroup):
    waiting_for_criteria = State()


@router.message(Command("menu", prefix="!/"), IsBotFilter(config.BOT_TOKEN_PARTNER))
async def show_main_menu(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    """Главное меню бота"""
    data = await get_storage_data(message, state, database)
    prefered_name = data.get("name")
    lang_code = data.get("lang_code")

    greeting = MESSAGES["hello"][lang_code] + " <b>" + prefered_name + "</b>!"
    intro = MESSAGES["intro"][lang_code]
    await state.update_data(
        lang_code=lang_code,
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
    )
    await message.answer(
        text=greeting + "\n\n" + intro,
        parse_mode=ParseMode.HTML,
        reply_markup=show_partner_menu_keyboard(lang_code),
    )


@router.message(Command("start", prefix="!/"), IsBotFilter(config.BOT_TOKEN_PARTNER))
async def start(message: Message, state: FSMContext, database: ResourcesMiddleware):
    if await database.check_profile_exists(message.from_user.id):
        return await show_main_menu(message, state, database)

    user_id = message.from_user.id
    lang_code = message.from_user.language_code
    greeting = (
        f"{MESSAGES['hello'][lang_code]} <b>{message.from_user.first_name}</b>!\n\n"
        f"{MESSAGES['intro'][lang_code]}\n"
    )
    await message.answer(text=greeting, parse_mode=ParseMode.HTML)
    if not await database.check_profile_exists(user_id):
        # Обновляем user_id в состоянии
        await state.update_data(user_id=user_id, lang_code=lang_code)
        # Отправляем приветственное сообщение
        txt = QUESTIONARY["need_profile"][lang_code]
        await message.answer(text=txt, parse_mode=ParseMode.HTML)
        # Переходим в состояние ожидания имени
        return await state.set_state(PollingState.waiting_for_name)


@router.message(PollingState.waiting_for_name, IsBotFilter(config.BOT_TOKEN_PARTNER))
async def process_name(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if len(message.text) <= 50 and re.sub(r"\s", "", message.text) == message.text:
        await state.update_data(name=message.text)
        msg = QUESTIONARY["need_age"][lang_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return await state.set_state(PollingState.waiting_for_bday)

    msg = MESSAGES["wrong_name"][lang_code]
    await message.reply(text=msg, parse_mode=ParseMode.HTML)


@router.message(PollingState.waiting_for_bday, IsBotFilter(config.BOT_TOKEN_PARTNER))
async def process_age(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", message.text):
        await state.update_data(bday=message.text)
        await message.answer(
            text=QUESTIONARY["need_intro"][lang_code], parse_mode=ParseMode.HTML
        )
        return await state.set_state(PollingState.waiting_for_intro)

    msg = MESSAGES["wrong_birthday"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)


@router.message(PollingState.waiting_for_intro, IsBotFilter(config.BOT_TOKEN_PARTNER))
async def process_intro(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if re.search(r"\S{10,500}", message.text):
        msg = QUESTIONARY["need_dating"][lang_code]
        await message.answer(
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=show_dating_keyboard(lang_code),
        )
        await state.update_data(intro=message.text)
        return await state.set_state(PollingState.waiting_for_dating)

    msg = MESSAGES["wrong_intro"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)


@router.message(
    PollingState.waiting_for_dating,
    IsBotFilter(config.BOT_TOKEN_PARTNER),
    lambda message: message.text
    == BUTTONS["yes_to_dating"][message.from_user.language_code],
)
async def agreed_to_dating_handler(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id", 0)
    name = data.get("name", "default")
    birthday = datetime.strptime(data.get("bday", "01.01.1800"), "%d.%m.%Y").date()
    intro = data.get("intro", "non-existent")
    lang_code = data.get("lang_code", "en")
    # Сохраняем профиль
    await database.add_users_profile(user_id, name, birthday, about=intro, dating=True)

    location_exists: bool = await database.check_location_exists(user_id)
    if not location_exists:
        msg = QUESTIONARY["need_location"][lang_code]
        await message.answer(
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=show_location_keyboard(lang_code),
        )
        return await state.set_state(PollingState.waiting_for_location)

    # Если локация каким-то образом существует, то переходим в главное меню
    else:
        await show_main_menu(message, state, database)


@router.message(
    PollingState.waiting_for_dating,
    IsBotFilter(config.BOT_TOKEN_PARTNER),
    lambda message: message.text
    == BUTTONS["no_to_dating"][message.from_user.language_code],
)
async def disagreed_to_dating_handler(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id", 0)
    name = data.get("name", "default")
    birthday = datetime.strptime(data.get("bday", "01.01.1800"), "%d.%m.%Y").date()
    intro = data.get("intro", "non-existent")
    lang_code = data.get("lang_code", "en")
    # Сохраняем профиль
    await database.add_users_profile(user_id, name, birthday, about=intro)
    msg = MESSAGES["no_worries_dating"][lang_code]
    await message.answer(
        text=msg, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove()
    )


@router.message(
    PollingState.waiting_for_location, F.location, IsBotFilter(config.BOT_TOKEN_PARTNER)
)
async def process_location(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    """Обработчик локации"""
    data = await state.get_data()
    user_id = data.get("user_id", 0)
    lang_code = data.get("lang_code", "en")
    # Сохраняем координаты в БД
    lattitude = str(message.location.latitude)
    longitude = str(message.location.longitude)
    await database.add_users_location(user_id, lattitude, longitude)
    # Выводим благодарное сообщение
    msg = MESSAGES["success"][lang_code]
    await message.answer(text=msg, reply_markup=ReplyKeyboardRemove())


@router.message(
    PollingState.waiting_for_location,
    IsBotFilter(config.BOT_TOKEN_PARTNER),
    lambda message: message.text
    == BUTTONS["cancel"].get(message.from_user.language_code, BUTTONS["cancel"]["en"]),
)
async def cancel(message: Message, state: FSMContext, database: ResourcesMiddleware):
    msg = MESSAGES["no_worries"][message.from_user.language_code]
    await database.add_users_location(message.from_user.id, "refused", "refused")
    await message.reply(text=msg, reply_markup=ReplyKeyboardRemove())


@router.message(Command("location", prefix="!/"), IsBotFilter(config.BOT_TOKEN_PARTNER))
async def get_my_location(message: Message, database: ResourcesMiddleware):
    """Обработчик команды /location"""
    lang_code = message.from_user.language_code
    result = await database.get_users_location(message.from_user.id)
    if result is None or result["latitude"] == "refused":
        await message.answer(text="You didn't share your location")
        return
    latitude = result["latitude"]
    longitude = result["longitude"]

    msg = MESSAGES["your_location"][lang_code]
    await message.answer(
        text=f"{msg}: <b>{latitude}</b>, <b>{longitude}</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(
    Command("new_session", prefix="!/"), IsBotFilter(config.BOT_TOKEN_PARTNER)
)
async def new_session_handler(
    message: Message,
    state: FSMContext,
    redis: ResourcesMiddleware,
    http_session: ResourcesMiddleware,
    database: ResourcesMiddleware,
):
    """Обработчик команды /new_session - запускает поиск партнера"""
    data = await get_storage_data(message, state, database)
    user_id = data.get("user_id", 0)
    username = data.get("username", "daniel")
    language = data.get("language")
    dating = data.get("dating", "false")

    if username == "NO USERNAME":
        msg = MESSAGES["no_username"][message.from_user.language_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return

    # Отменяем предыдущий поиск, если он был
    active_tasks = await redis.get(f"active_search_tasks:{user_id}")
    if active_tasks and username in str(active_tasks.decode()):
        await redis.delete(f"active_search_tasks:{user_id}")
        logger.debug(f"Отменен предыдущий поиск для пользователя {user_id}")

    await redis.setex(f"active_search_tasks:{user_id}", 180, username)
    logger.debug(f"Создана сессия поиска для пользователя {user_id}")

    await message.answer(
        f"🔍 Ищем партнера для общения на <b>{language}</b>...",
        parse_mode=ParseMode.HTML,
    )

    # Отправляю запрос на сервер
    url = "{DOMAIN}/match".format(DOMAIN=os.getenv("BASE_DOMAIN", "0.0.0.0"))

    payload = {
        "user_id": int(user_id),
        "username": username,
        "criteria": {
            "dating": dating,
            "language": language,
            "topic": "general",
        },
    }

    async with http_session.post(url=url, json=payload) as response:
        if response.status != 200:
            logger.error(f"Ошибка при запросе к API: {response.status}")
            # Обработка ошибки


@router.message(IsBotFilter(config.BOT_TOKEN_PARTNER))
async def echo(message: Message, rate_limit_info: RateLimitInfo):
    # Убираем кнопки после любого сообщения

    if message.text:
        await message.copy_to(message.chat.id)
    count = rate_limit_info.message_count
    first_message = rate_limit_info.last_message_time
    await message.reply(
        text=f"Your message: {message.text}\n"
        f"Rate limit info: {count} messages at {first_message}",
    )
