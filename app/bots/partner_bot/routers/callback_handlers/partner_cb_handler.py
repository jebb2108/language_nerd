import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.dependencies import get_redis
from config import LOG_CONFIG, config
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.utils.filters import IsBotFilter
from app.bots.partner_bot.utils.access_data import data_storage
from app.bots.partner_bot.translations import MESSAGES


from app.bots.partner_bot.keyboards.inline_keyboards import (
    get_go_back_keyboard,
    show_partner_menu_keyboard,
)

router = Router(name=__name__)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="partner_cb_handler")


@router.callback_query(F.data == "main_bot", IsBotFilter(config.BOT_TOKEN_PARTNER))
async def main_menu_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "profile", IsBotFilter(config.BOT_TOKEN_PARTNER))
async def profile_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    nickname = data["name"]
    age = " " * 14 + str(data["age"])
    fluency = " " * 7 + data["fluency"]
    status = " " * 8 + data["status"]
    level_status = f"[🟩🟩🟩🟩⬜⬜]\nСледующий уровень: 40%\n"
    msg = (
        f"=== {nickname} ===\n\n"
        f"{level_status}\n"
        f"Age: {age}\nFluency: {fluency}\nStatus: {status}"
    )
    await callback.answer(text=msg, show_alert=True)


@router.callback_query(F.data == "about", IsBotFilter(config.BOT_TOKEN_PARTNER))
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


@router.callback_query(F.data == "go_back", IsBotFilter(config.BOT_TOKEN_PARTNER))
async def go_back_handler(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):

    await callback.answer()

    user_id = callback.from_user.id
    data = await data_storage.get_storage_data(user_id, state, database)
    lang_code = data.get("lang_code", "en")
    prefered_name = data.get("pref_name", "User")

    msg = MESSAGES["hello"][lang_code] + " <b>" + prefered_name + "</b>!\n\n"
    msg += MESSAGES["intro"][lang_code]

    await callback.message.edit_text(
        text=msg,
        reply_markup=show_partner_menu_keyboard(lang_code),
    )

@router.callback_query(F.data == "queue_info", IsBotFilter(config.BOT_TOKEN_PARTNER))
async def show_queue_info(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
        redis: ResourcesMiddleware
):

    queue = await redis.lrange("waiting_queue", 0, -1)
    queue = [ int(user_id.decode()) for user_id in queue ]

    common_lans = dict()

    data = await data_storage.get_storage_data(callback.from_user.id, state, database)
    lang_code = data.get("lang_code", "en")
    for user_id in queue:
        language = await database.get_user_info(user_id)
        if language not in common_lans:
            common_lans[language] = 0
        else:
            common_lans[language] += 1

    lans = sorted(common_lans, reverse=True)[:5]
    s_lans = ", ".join(lans)
    s_lans = s_lans if s_lans else MESSAGES['nobody_in_queue'][lang_code]
    text = MESSAGES['show_queue_info'][lang_code].format(total=len(queue), lans=s_lans)
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

    """Обработчик команды /new_session - запускает поиск партнера"""

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

    await message.edit_text(text=MESSAGES['cancel'][lang_code])

    # Отправляю запрос на сервер
    url = "{DOMAIN}/cancel".format(DOMAIN=config.BASE_URL)

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
