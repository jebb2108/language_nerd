import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.main import redis
from app.services.rabbitmq import RabbitMQService
from app.dependencies import get_rabbitmq, get_db, get_redis, get_match
from app.models import UserMatchRequest, ChatSessionRequest
from app.validators.create_token import create_token
from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger("endpoints")

router = APIRouter()


@router.post("/match")
async def request_match(
    request: UserMatchRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq),
    db=Depends(get_db),
):
    logger.warning(
        f"Получен запрос на поиск партнера для пользователя {request.user_id}"
    )
    # Проверяем пользователя в БД
    user = await db.check_user_exists(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.warning(f"User ID: {request.user_id}, criteria: {request.criteria}")

    # Сохраняем статус поиска в Redis
    # ( На этом уровне мы можем работать только с методами класса,
    # которые ввзаимодействуют с Redis )
    await redis.add_to_queue(request.user_id, request.criteria)

    # Отправляем запрос в очередь
    message = {
        "user_id": request.user_id,
        "username": request.username,
        "criteria": request.criteria,
        "created_at": datetime.now(tz=config.TZINFO).isoformat(), # переводит в строку
        "status": config.SEARCH_STARTED,
    }

    await rabbitmq.publish_message(message)


@router.post("/notify")
async def notify_users_re_match(
    request: ChatSessionRequest,
    db=Depends(get_db),
    redis=Depends(get_redis),
    rabbitmq=Depends(get_rabbitmq)
):
    await redis.create_chat_session(request.user1_id, request.user2_id, request.room_id)
    logger.info(
        f"Создана сессия чата для пользователей {request.user1_id} и {request.user2_id}"
    )
    from aiogram import Bot
    from app.bots.partner_bot.keyboards.inline_keyboards import create_start_chat_button
    from app.bots.partner_bot.translations import MESSAGES

    users_exists = await db.check_user_exists(
        request.user1_id
    ) and await db.check_user_exists(request.user2_id)
    if users_exists:

        room_id = request.room_id
        link = "https://chat.lllang.site/enter/{room_id}?token={token}"

        bot = Bot(token=config.BOT_TOKEN_PARTNER)

        user1_data = await db.get_user_info(request.user1_id)
        lang_code1 = user1_data["lang_code"]
        user2_data = await db.get_user_info(request.user2_id)
        lang_code2 = user2_data["lang_code"]

        link1 = link.format(
            room_id=room_id, token=await create_token(request.user1_id, room_id)
        )
        link2 = link.format(
            room_id=room_id, token=await create_token(request.user2_id, room_id)
        )

        logger.warning("first_link: %s", link1)
        logger.warning("second link %s", link2)

        msg1 = MESSAGES["match_found"][lang_code1]
        msg2 = MESSAGES["match_found"][lang_code2]

        await bot.send_message(
            chat_id=request.user1_id,
            text=msg1.format(nickname=user2_data["username"]),
            reply_markup=create_start_chat_button(lang_code1, link1),
            parse_mode="HTML",
        )
        await bot.send_message(
            chat_id=request.user2_id,
            text=msg2.format(nickname=user1_data["username"]),
            reply_markup=create_start_chat_button(lang_code2, link2),
            parse_mode="HTML",
        )

        # Отправляем запрос в очередь
        message = {
            "user_id": request.user_id,
            "username": request.username,
            "criteria": request.criteria,
            "created_at": datetime.now(tz=config.TZINFO).isoformat(),  # переводит в строку
            "status": config.SEARCH_COMPLETED,
        }

        await rabbitmq.publish_message(message)



    return {"status": "notification_sent"}


@router.post("/cancel")
async def request_match(
    request: UserMatchRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq),
    db=Depends(get_db),
):
    # Проверяем пользователя в БД
    user = await db.check_user_exists(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Отправляем запрос в очередь
    message = {
        "user_id": request.user_id,
        "username": request.username,
        "criteria": request.criteria,
        "created_at": datetime.now(tz=config.TZINFO).isoformat(),
        "status": config.SEARCH_CANCELED,
    }

    await rabbitmq.publish_message(message)
