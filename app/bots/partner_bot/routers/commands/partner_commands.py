from typing import Union

import aiohttp
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, and_f
from aiogram.enums import ParseMode

from app.bots.main_bot.filters.paytime import paytime
from app.bots.partner_bot.keyboards.inline_keyboards import show_topic_keyboard
from app.bots.partner_bot.utils.exc import StorageDataException
from app.dependencies import get_db, get_redis_client
from app.models import UserMatchRequest
from app.bots.partner_bot.utils.access_data import data_storage as ds
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
async def change_topic_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        topic = data.get("topic")
        msg = MESSAGES["current_topic"][lang_code].format(
            topic=TRANSCRIPTIONS["topics"][topic][lang_code]
        )
        await message.answer(
            text=msg, reply_markup=show_topic_keyboard(lang_code), parse_mode=ParseMode.HTML
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await message.answer("You`re not registered. Press /start to do")

    except Exception as e:
        logger.error(f"Error in change_topic_handler: {e}")


@router.message(and_f(Command("new_session", prefix="!/"), paytime))
async def new_session_handler(
    message: Union[Message, CallbackQuery], state: FSMContext
):
    """Обработчик команды /new_session - запускает поиск партнера"""

    user_id = message.from_user.id
    database = await get_db()
    redis_client = await get_redis_client()

    try:
        data = await ds.get_storage_data(user_id, state)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        return await message.answer("You`re not registered. Press /start to do so")

    else:
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
            return logger.error(f"Исключение при выполнении запроса: {e}")


