import logging

from typing import Union

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import config, LOG_CONFIG
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.main_bot.utils.filters import IsBotFilter
from app.bots.partner_bot.translations import MESSAGES

from app.bots.partner_bot.keyboards.inline_keyboards import (
    show_partner_menu_keyboard,
    get_search_keyboard,
)

from app.bots.partner_bot.utils.access_data import data_storage

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(config.BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(config.BOT_TOKEN_PARTNER))

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="partner_commands")


@router.message(Command("menu", prefix="!/"), IsBotFilter(config.BOT_TOKEN_PARTNER))
async def show_main_menu(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    """Главное меню бота"""
    user_id = message.from_user.id
    data = await data_storage.get_storage_data(user_id, state, database)
    prefered_name = data.get("pref_name")
    lang_code = data.get("lang_code")

    greeting = MESSAGES["hello"][lang_code] + " <b>" + prefered_name + "</b>!"
    intro = MESSAGES["intro"][lang_code]
    await state.update_data(
        user_id=user_id,
        lang_code=lang_code,
        first_name=message.from_user.first_name,
    )
    await message.answer(
        text=greeting + "\n\n" + intro,
        parse_mode=ParseMode.HTML,
        reply_markup=show_partner_menu_keyboard(lang_code),
    )


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
    message: Union[Message, CallbackQuery],
    state: FSMContext,
    redis: ResourcesMiddleware,
    http_session: ResourcesMiddleware,
    database: ResourcesMiddleware,
):
    """Обработчик команды /new_session - запускает поиск партнера"""

    data = await data_storage.get_storage_data(message.from_user.id, state, database)
    user_id = data.get("user_id", 0)
    username = data.get("username", "daniel")
    language = data.get("language", "english")
    dating = data.get("dating", "false")
    topic = data.get("topic", "general")
    lang_code = data.get("lang_code", "en")

    if username == "NO USERNAME":
        msg = MESSAGES["no_username"][message.from_user.language_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return

    # Отменяем предыдущий поиск, если он был
    is_searching = await redis.get(f"searching:{user_id}")
    if is_searching:
        await redis.delete(f"searching:{user_id}")
        logger.debug(f"Отменен предыдущий поиск для пользователя {user_id}")

    await redis.setex(f"searching:{user_id}", 150, username)
    logger.debug(f"Создана сессия поиска для пользователя {user_id}")

    await message.answer(
        f"🔍 Ищем партнера для общения - <b>{language}</b>\n\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_search_keyboard(lang_code),
    )

    # Отправляю запрос на сервер
    url = "{DOMAIN}/match".format(DOMAIN=config.BASE_URL)

    payload = {
        "user_id": int(user_id),
        "username": username,
        "criteria": {
            "dating": dating,
            "language": language,
            "topic": topic,
        },
    }

    logger.warning(f"Отправка запроса на: {url}")
    logger.warning(f"Данные запроса: {payload}")

    try:
        async with http_session.post(url=url, json=payload, headers={'Content-Type': 'application/json'}) as response:
            response_text = await response.text()
            logger.warning(f"Статус ответа: {response.status}")
            logger.warning(f"Тело ответа: {response_text}")

            if response.status != 200:
                logger.error(f"Ошибка при запросе к API: {response.status}. Ответ: {response_text}")
            else:
                logger.info("Запрос успешно обработан")

    except Exception as e:
        logger.error(f"Исключение при выполнении запроса: {e}")