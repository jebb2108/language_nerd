import asyncio

import aiohttp
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.filters.approved import approved
from app.bot.keyboards.inline_keyboards import show_topic_keyboard
from app.bot.routers.commands.menu_commands import MultiSelection
from app.bot.translations import MESSAGES, TRANSCRIPTIONS
from app.bot.utils.access_data import data_storage as ds
from app.dependencies import get_db, get_redis_client
from app.models import UserMatchRequest
from config import config
from exc import StorageDataException
from logging_config import opt_logger as log

logger = log.setup_logger("additional_cb_handler")

router = Router(name=__name__)



@router.callback_query(and_f(F.data == "queue_info", approved))
async def show_queue_info_handler(callback: CallbackQuery, state: FSMContext):

    common_lans = dict()
    database = await get_db()
    redis = await get_redis_client()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        queue = await redis.lrange("waiting_queue", 0, -1)
        lang_code = data.get("lang_code", "en")
        for user_id in map(int, queue):
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

    except StorageDataException:
        logger.error(f"User {user_id} trying access data")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in show_queue_info_handler: {e}")


@router.callback_query(F.data.startswith("profile_change:"))
async def profile_change_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        users_choice = callback.data.split(":")[1]

        if users_choice == "topics":
            all_topics = data.get("topics").split(', ')
            topics = [TRANSCRIPTIONS["topics"][topic][lang_code] for topic in all_topics]

            msg = MESSAGES["current_topic"][lang_code].format(
                topic=", ".join(topics)
            )
            await state.update_data(new_topics=[])
            await callback.message.edit_caption(
                caption=msg, reply_markup=show_topic_keyboard(
                    lang_code, selected_options=[], new=True)
                , parse_mode=ParseMode.HTML
            )

            await state.set_state(MultiSelection.waiting_selection)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in cancel_choosing_topic: {e}")



@router.callback_query(
    and_f(F.data.startswith("chtopic_"), MultiSelection.waiting_selection, approved)
)
async def change_topic_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    database = await get_db()
    user_id = callback.from_user.id
    users_choice = callback.data.split("_")[1]

    try:
        data = await state.get_data()
        lang_code = data.get("lang_code")
        new_topics = data.get("new_topics", [])
        if users_choice not in new_topics:
            new_topics.append(users_choice)
        if len(new_topics) > 3: new_topics.pop(0)
        if users_choice == "endselection":
            new_topics.remove("endselection")
            profile_data = await ds.get_storage_data(user_id, state)

            if set(profile_data.get("topics").split(", ")) != set(new_topics):
                await database.change_topic(user_id, new_topics)
                msg = MESSAGES["topic_changed"][lang_code]

                await state.update_data(new_topics=[], topics=", ".join(new_topics))
                await callback.message.edit_caption(caption=msg)
                return await state.update_data(topic=users_choice)


            return await callback.message.edit_caption(
                caption=MESSAGES["fail_to_change"][lang_code]
            )

        await state.update_data(new_topics=new_topics)
        await callback.message.edit_reply_markup(
            reply_markup=show_topic_keyboard(
                lang_code, selected_options=new_topics, new=True)
        )
        await state.set_state(MultiSelection.waiting_selection)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in change_topic handler: {e}")



@router.callback_query(and_f(F.data == "cancel_topic", approved))
async def cancel_choosing_topic(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    await callback.message.delete()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        await callback.message.answer(text=MESSAGES["topic_change_canceled"][lang_code])

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in cancel_choosing_topic: {e}")


@router.callback_query(and_f(F.data == "cancel", approved))
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback(а) отменяет поиск партнера"""

    await callback.answer()
    user_id = callback.from_user.id
    redis_client = await get_redis_client()


    try:
        data = await ds.get_storage_data(user_id, state)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    else:
        user_id = data.get("user_id")
        username = data.get("username")
        language = data.get("language")
        fluency = data.get("fluency")
        topic = data.get("topic")
        dating = str(data.get("dating"))
        gender = data.get("gender") or "unknown"
        lang_code = data.get("lang_code")

        await callback.message.edit_text(text=MESSAGES["cancel_search"][lang_code])

        # Отправляю запрос на сервер
        headers = {"Content-Type": "application/json"}
        payload = UserMatchRequest(
            status=config.SEARCH_CANCELED,
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

        is_searching = await redis_client.get(f"searching:{user_id}")
        if is_searching:
            await redis_client.delete(f"searching:{user_id}")
            logger.debug(f"Отменен поиск для пользователя {user_id}")

        logger.info(f"Отправка запроса на: {url}")
        logger.debug(f"Данные запроса: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
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
                        await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Исключение при выполнении запроса: {e}")
