import asyncio
from typing import TYPE_CHECKING
from aiogram.enums import ParseMode
from fastapi import APIRouter, Depends, HTTPException

from app.models import UserMatchResponse
from app.dependencies import get_rabbitmq, get_db, get_redis, get_partner_bot
# from app.bots.main_bot.keyboards.inline_keyboards import create_start_chat_button
from app.bots.partner_bot.translations import MESSAGES
from app.services.database import DatabaseService
from app.services.redis import RedisService
# from app.validators.tokens import create_token
from config import config
from logging_config import opt_logger as log
from app.models import UserMatchRequest, RegistrationData
from app.services.rabbitmq import RabbitMQService

if TYPE_CHECKING:
    from aiogram import Bot

logger = log.setup_logger("endpoints", config.LOG_LEVEL)


router = APIRouter(prefix="/api")


@router.get("/check_user")
async def check_user(user_id: str, database: "DatabaseService" = Depends(get_db)):
    """Проверяет, существует ли пользователь в БД"""
    exists = await database.check_profile_exists(int(user_id))
    return {"exists": exists}

@router.post("/register")
async def register_user(
        user_data: RegistrationData,
        database: "DatabaseService" = Depends(get_db),
):
    # Сохранение в базу данных профиля пользователя
    await database.add_users_profile(**user_data.model_dump(exclude_none=True))
    return {"message": "Пользователь успешно зарегистрирован", "status": "success"}


@router.post("/match")
async def request_match(
    request: "UserMatchRequest",
    database: "DatabaseService" = Depends(get_db),
    rabbitmq: "RabbitMQService" = Depends(get_rabbitmq),
):
    # Проверяем пользователя в Redis
    user = await database.check_user_exists(user_id=request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found")

    logger.debug(
        f"User ID: {request.user_id}, "
        f"criteria: {request.criteria}, "
        f"gender: {request.gender},"
        f"lang_code: {request.lang_code}"
    )
    # Сохраняем статус поиска в Redis
    # ( На этом уровне мы можем работать только с методами класса,
    # которые ввзаимодействуют с Redis )
    redis = await get_redis()
    is_searching = True if request.status == config.SEARCH_STARTED else False
    if is_searching:
        logger.info(f"Получен запрос на поиск партнера для пользователя {request.user_id}")
        await redis.add_to_queue(request)
    # Отправляем запрос в очередь
    await rabbitmq.publish_request(request.model_dump())
    return {"status": "user added to queue"}


@router.delete("/match")
async def cancel_match(
    request: UserMatchRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq),
    redis: "RedisService" = Depends(get_redis),
):
    logger.info(f"Поступил запрос на выход из очереди от пользователя {request.user_id}")

    logger.debug(
        f"User ID: {request.user_id}, "
        f"criteria: {request.criteria}, "
        f"gender: {request.gender},"
        f"lang_code: {request.lang_code}"
    )

    # Отправляем сообщение в очередь
    await rabbitmq.publish_request(request.model_dump())
    await redis.remove_from_queue(request.user_id)
    return {"status": "User deleted from queue"}


@router.post("/timed_out")
async def exit_match(
    data: "UserMatchResponse", redis: "RedisService" = Depends(get_redis)
):

    user_id = data.user_id
    lang_code = data.lang_code

    curr_search_msg = await redis.get_search_message_id(user_id)
    if not curr_search_msg:
        raise HTTPException(status_code=404, detail=f"Message not found {user_id}")

    bot: "Bot" = await get_partner_bot()

    await bot.delete_message(chat_id=user_id, message_id=curr_search_msg)

    await asyncio.sleep(0.5)

    message = await bot.send_message(
        chat_id=user_id,
        text=MESSAGES["timed_out"][lang_code],
        parse_mode=ParseMode.HTML,
    )

    await redis.remove_from_queue(user_id=user_id)
    # Сохраняем текущее сообщение в очереди
    # для последующего удаления при новой сессии поиска
    await redis.save_sent_message(message)


# @router.post("/notify")
# async def notify_users_re_match(
#     request: dict,
#     db: "DatabaseService" = Depends(get_db),
#     redis: "RedisService" = Depends(get_redis),
# ):
#
#     room_id = request["room_id"]
#     user_data = request["user"]
#     partner_data = request["partner"]
#
#     user_id = int(user_data["user_id"])
#     partner_id = int(partner_data["user_id"])
#
#     link = "https://chat.lllang.site/enter/{room_id}?token={token}"
#
#     user_profile = await db.get_all_user_info(user_id)
#     partner_profile = await db.get_all_user_info(partner_id)
#     # Ссылки для подключения
#     user_link = link.format(room_id=room_id, token=await create_token(user_id, room_id))
#     partner_link = link.format(
#         room_id=room_id, token=await create_token(partner_id, room_id)
#     )
#     # Никнеймы, видимые партнеру
#     user_nickname = user_profile.get("nickname")
#     partner_nickname = partner_profile.get("nickname")
#     # Извлекаю описание пользователю
#     about_user = user_profile.get("about")
#     about_partner = partner_profile.get("about")
#     # Создаю сообщения
#     user_msg = MESSAGES["match_found"][user_data.get("lang_code")]
#     partner_msg = MESSAGES["match_found"][partner_data.get("lang_code")]
#
#     prev_users_msg_id = await redis.get_search_message_id(user_id)
#     prev_partners_msg_id = await redis.get_search_message_id(partner_id)
#
#     try:
#
#         bot: "Bot" = await get_partner_bot()
#
#         await bot.delete_message(chat_id=user_id, message_id=prev_users_msg_id)
#
#         await bot.delete_message(chat_id=partner_id, message_id=prev_partners_msg_id)
#
#         # Ожидаем некоторое время перед отправкой
#         # для хорошего визуального эффека
#         await asyncio.sleep(0.5)
#
#         await bot.send_message(
#             chat_id=user_id,
#             text=user_msg.format(nickname=partner_nickname, about=about_partner),
#             reply_markup=create_start_chat_button(
#                 # Отправляем сообщение с клавиатурой
#                 # на языке пользователя со ссылкой
#                 user_data.get("lang_code"),
#                 link=user_link,
#             ),
#             parse_mode=ParseMode.HTML,
#         )
#
#         await bot.send_message(
#             chat_id=partner_id,
#             text=partner_msg.format(nickname=user_nickname, about=about_user),
#             reply_markup=create_start_chat_button(
#                 # Отправляем сообщение с клавиатурой
#                 # на языке пользователя со ссылкой
#                 lang_code=partner_data["lang_code"],
#                 link=partner_link,
#             ),
#             parse_mode=ParseMode.HTML,
#         )
#
#     except Exception as e:
#         logger.error(f"Error launching chat for users: {e}")
#         raise HTTPException(
#             status_code=500, detail="notification wasn't sent due to error"
#         )
#
#     finally:
#         await redis.remove_from_queue(user_id)
#         await redis.remove_from_queue(partner_id)
#         return {"status": "notification_sent"}
