import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.dependencies import get_redis
from config import LOG_CONFIG, config
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.utils.access_data import data_storage
from app.bots.partner_bot.translations import MESSAGES, TRANSCRIPTIONS

from app.bots.partner_bot.keyboards.inline_keyboards import (
    get_go_back_keyboard,
    show_partner_menu_keyboard,
    get_search_keyboard,
)

router = Router(name=__name__)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="partner_cb_handler")


@router.callback_query(F.data == "main_bot")
async def main_menu_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "profile")
async def profile_handler(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):

    await callback.answer()
    user_id = callback.message.from_user.id
    data = await data_storage.get_storage_data(
        user_id=user_id, state=state, database=database
    )
    lang_code = data.get("lang_code", "en")

    msg = MESSAGES["user_info"][lang_code].format(
        level_status=f"[🟩🟩🟩🟩⬜⬜]",
        percentage="40%",
        nickname=data.get("pref_name"),
        age=data.get("age"),
        fluency=TRANSCRIPTIONS["fluency"][data.get("fluency")][lang_code],
        topic=TRANSCRIPTIONS["topics"][data.get("topic")][lang_code],
        status=TRANSCRIPTIONS["status"][data.get("status")][lang_code],
        language=TRANSCRIPTIONS["languages"][data.get("language")][lang_code],
        about=data.get("about"),
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=get_go_back_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "about")
async def about_handler(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):

    await callback.answer()

    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state, database)
    lang_code = data.get("lang_code", "en")

    await callback.message.edit_text(
        text=MESSAGES["about"][lang_code],
        reply_markup=get_go_back_keyboard(lang_code),
    )


@router.callback_query(F.data == "go_back")
async def go_back_handler(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):

    await callback.answer()

    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state, database)
    language = data.get("language")
    lang_code = data.get("lang_code", "en")
    prefered_name = data.get("pref_name", "User")

    msg = MESSAGES["hello"][language] + " <b>" + prefered_name + "</b>!\n\n"
    msg += MESSAGES["intro"][lang_code]

    await callback.message.edit_text(
        text=msg,
        reply_markup=show_partner_menu_keyboard(lang_code),
    )


@router.callback_query(F.data == "queue_info")
async def show_queue_info(
    callback: CallbackQuery,
    state: FSMContext,
    database: ResourcesMiddleware,
    redis: ResourcesMiddleware,
):

    queue = await redis.lrange("waiting_queue", 0, -1)
    queue = [int(user_id.decode()) for user_id in queue]

    common_lans = dict()

    data = await data_storage.get_storage_data(callback.from_user.id, state, database)
    lang_code = data.get("lang_code", "en")
    for user_id in queue:
        user_info = await database.get_user_info(user_id)
        lan = user_info["language"]
        if lan not in common_lans:
            common_lans[lan] = 0
        else:
            common_lans[lan] += 1

    lans = sorted(common_lans, reverse=True)[:5]
    s_lans = ", ".join(lans)
    s_lans = s_lans if s_lans else MESSAGES["nobody_in_queue"][lang_code]
    total = str(len(queue)) if len(queue) != 1 else MESSAGES["its_just_you"][lang_code]
    text = MESSAGES["show_queue_info"][lang_code].format(total=total, lans=s_lans)
    await callback.answer(text=text, show_alert=True)


@router.callback_query(F.data == "cancel")
async def cancel_search(
    callback: CallbackQuery,
    state: FSMContext,
    database: ResourcesMiddleware,
    http_session: ResourcesMiddleware,
):
    await callback.answer()

    message = callback.message

    redis = await get_redis(call_client=True)

    """Обработчик callback(а) отменяет поиск партнера"""

    data = await data_storage.get_storage_data(message.from_user.id, state, database)
    user_id = data.get("user_id", 0)
    username = data.get("username", "daniel")
    language = data.get("language", "english")
    dating = data.get("dating", "false")
    lang_code = data.get("lang_code", "en")

    # Отменяем предыдущий поиск, если он был
    is_searching = await redis.get(f"searching:{user_id}")
    if is_searching:
        await redis.delete(f"searching:{user_id}")
        logger.debug(f"Отменен предыдущий поиск для пользователя {user_id}")

    await message.edit_text(text=MESSAGES["cancel_search"][lang_code])

    # Отправляю запрос на сервер
    url = "{DOMAIN}/cancel".format(DOMAIN=f"{config.BASE_URL}{config.BASE_PORT}")

    payload = {
        "user_id": int(user_id),
        "username": username,
        "criteria": {
            "dating": dating,
            "language": language,
            "topic": "general",
        },
    }

    try:
        async with http_session.post(
            url=url, json=payload, headers={"Content-Type": "application/json"}
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


@router.callback_query(F.data == "begin_search")
async def new_session_handler(
    callback: CallbackQuery,
    state: FSMContext,
    redis: ResourcesMiddleware,
    http_session: ResourcesMiddleware,
    database: ResourcesMiddleware,
):
    """Обработчик команды /new_session - запускает поиск партнера"""

    await callback.answer()

    data = await data_storage.get_storage_data(callback.from_user.id, state, database)
    user_id = data.get("user_id", 0)
    username = data.get("username", "daniel")
    language = data.get("language", "english")
    dating = data.get("dating", "false")
    lang_code = data.get("lang_code", "en")

    if username == "NO USERNAME":
        msg = MESSAGES["no_username"][callback.from_user.language_code]
        await callback.message.answer(text=msg, parse_mode=ParseMode.HTML)
        return

    # Отменяем предыдущий поиск, если он был
    is_searching = await redis.get(f"searching:{user_id}")
    if is_searching:
        await redis.delete(f"searching:{user_id}")
        logger.debug(f"Отменен предыдущий поиск для пользователя {user_id}")

    await redis.setex(f"searching:{user_id}", 150, username)
    logger.debug(f"Создана сессия поиска для пользователя {user_id}")

    await callback.message.answer(
        f"🔍 Ищем партнера для общения - <b>{language}</b>\n\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_search_keyboard(lang_code),
    )

    # Отправляю запрос на сервер
    url = "{DOMAIN}/match".format(DOMAIN=f"{config.BASE_URL}{config.BASE_PORT}")

    payload = {
        "user_id": int(user_id),
        "username": username,
        "criteria": {
            "dating": dating,
            "language": language,
            "topic": "general",
        },
    }

    logger.warning(f"Отправка запроса на: {url}")
    logger.warning(f"Данные запроса: {payload}")

    try:
        async with http_session.post(
            url=url, json=payload, headers={"Content-Type": "application/json"}
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
