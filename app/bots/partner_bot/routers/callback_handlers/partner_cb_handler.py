import aiohttp
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bots.main_bot.utils.exc import StorageDataException
from app.bots.partner_bot.filters.paytime import paytime
from app.dependencies import get_redis_client, get_db
from app.models import UserMatchRequest
from config import config
from app.bots.partner_bot.utils.access_data import data_storage as ds
from app.bots.partner_bot.translations import MESSAGES

from app.bots.partner_bot.keyboards.inline_keyboards import (
    get_go_back_keyboard,
    show_partner_menu_keyboard,
)
from app.bots.main_bot.keyboards.inline_keyboards import get_search_keyboard
from logging_config import opt_logger as log

router = Router(name=__name__)

logger = log.setup_logger("partner_cb_handler")


@router.callback_query(and_f(F.data == "about", paytime))
async def about_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code", "en")

        await callback.message.edit_caption(
            caption=MESSAGES["about"][lang_code],
            reply_markup=get_go_back_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but does`nt exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in about_handler: {e}")


@router.callback_query(and_f(F.data == "go_back", paytime))
async def go_back_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    user_id = callback.from_user.id

    try:

        data = await ds.get_storage_data(user_id, state)
        language = data.get("language")
        lang_code = data.get("lang_code")
        nickname = data.get("nickname")

        msg = MESSAGES["hello"][language] + " <b>" + nickname + "</b>!\n\n"
        msg += MESSAGES["full_intro"][lang_code]

        await callback.message.edit_caption(
            caption=msg,
            reply_markup=show_partner_menu_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in go_back_handler: {e}")




@router.callback_query(and_f(F.data == "begin_search", paytime))
async def new_session_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик команды /new_session - запускает поиск партнера"""

    await callback.answer()

    user_id = callback.from_user.id
    database = await get_db()
    redis_client = await get_redis_client()

    try:
        data = await ds.get_storage_data(user_id, state)

    except StorageDataException:
        logger.error(f"user {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    else:

        user_id = data.get("user_id")
        username = data.get("username")
        language = data.get("language")
        fluency = data.get("fluency")
        dating = str(data.get("dating"))
        gender = data.get("gender") or "unknown"
        topic = data.get("topic")
        lang_code = data.get("lang_code", "en")

        if username == "NO USERNAME":
            msg = MESSAGES["no_username"][lang_code]
            await callback.message.answer(text=msg, parse_mode=ParseMode.HTML)
            return

        if not await database.check_profile_exists(user_id):
            await callback.message.answer(
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

        # Отправляю запрос на сервер
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

        url = "{DOMAIN}/api/match".format(
            DOMAIN=f"{config.BASE_URL}:{config.CHAT_SERVER_PORT}"
        )

        logger.info(f"Отправка запроса на: {url}")
        logger.debug(f"Данные запроса: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url, json=payload.model_dump(), headers=headers
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Статус ответа: {response.status}")
                    logger.debug(f"Тело ответа: {response_text}")

                    if response.status != 200:
                        logger.error(
                            f"Ошибка при запросе к API: {response.status}. Ответ: {response_text}"
                        )
                    else:
                        logger.info("Запрос успешно обработан")

        except Exception as e:
            return logger.error(f"Исключение при выполнении запроса: {e}")

        return await callback.message.answer(
            text=MESSAGES["search_began"][lang_code],
            parse_mode=ParseMode.HTML,
            reply_markup=get_search_keyboard(lang_code),
        )


