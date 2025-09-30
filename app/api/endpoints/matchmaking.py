import logging
from datetime import datetime

from typing import TYPE_CHECKING
from aiogram.enums import ParseMode
from fastapi import APIRouter, Depends, HTTPException

from app.models import SentMessage
from app.services.rabbitmq import RabbitMQService
from app.dependencies import get_rabbitmq, get_db, get_redis, get_redis_client
from app.models.chat_models import UserMatchRequest, ChatSessionRequest
from app.bots.partner_bot.keyboards.inline_keyboards import create_start_chat_button
from app.bots.partner_bot.translations import MESSAGES
from app.validators.tokens import create_token
from config import LOG_CONFIG, config

if TYPE_CHECKING:
    from aiogram.types import Message

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger("endpoints")


router = APIRouter(prefix="/api")

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
    redis = await get_redis()
    await redis.add_to_queue(request.user_id, request.criteria)
    time_str = datetime.now(tz=config.TZINFO).isoformat()
    # Отправляем запрос в очередь
    message = {
        "user_id": request.user_id,
        "username": request.username,
        "criteria": request.criteria,
        "current_time": time_str,
        "created_at": time_str,
        "status": config.SEARCH_STARTED,
    }

    await rabbitmq.publish_message(message)
    return {"status": "user added to queue"}


@router.post("/cancel")
async def request_match(
    request: UserMatchRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    # Проверяем пользователя в БД
    user = await db.check_user_exists(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    time_str = datetime.now(tz=config.TZINFO).isoformat()
    # Отправляем запрос в очередь
    message = {
        "user_id": request.user_id,
        "username": request.username,
        "criteria": request.criteria,
        "current_time": time_str,
        "created_at": time_str,
        "status": config.SEARCH_CANCELED,
    }

    await rabbitmq.publish_message(message)
    await redis.remove_from_queue(request.user_id)
    return {"status": "User deleted from queue"}


@router.post("/notify")
async def notify_users_re_match(
    request: ChatSessionRequest,
    db=Depends(get_db),
    redis=Depends(get_redis)
):

    from aiogram import Bot

    users_exists = await db.check_user_exists(request.user_id)
    partner_exists = await db.check_user_exists(request.partner_id)
    if users_exists and partner_exists:

        room_id = request.room_id
        link = "https://chat.lllang.site/enter/{room_id}?token={token}"

        bot = Bot(token=config.BOT_TOKEN_PARTNER)

        user_data = await db.get_user_info(request.user_id)
        user_profile = await db.get_users_profile(request.user_id)
        lang_code1 = user_data.get("lang_code")
        partner_data = await db.get_user_info(request.partner_id)
        partner_profile = await db.get_users_profile(request.partner_id)
        lang_code2 = partner_data.get("lang_code")

        link1 = link.format(
            room_id=room_id, token=await create_token(request.user_id, room_id)
        )
        link2 = link.format(
            room_id=room_id, token=await create_token(request.partner_id, room_id)
        )

        logger.warning("first_link: %s", link1)
        logger.warning("second link %s", link2)

        msg1 = MESSAGES["match_found"][lang_code1]
        msg2 = MESSAGES["match_found"][lang_code2]

        users_nickname = user_profile.get("prefered_name")
        users_about = user_profile.get("about")
        partners_nickname = partner_profile.get("prefered_name")
        partners_about = partner_profile.get("about")

        prev_users_search_msg_id = await redis.get_search_message_id(request.user_id)
        prev_partners_msg_id = await redis.get_search_message_id(request.partner_id)

        logger.warning("users chat id %s", request.user_id)
        logger.warning("users search msg id: %s", int(prev_users_search_msg_id))

        logger.warning("partners chat id %s", request.partner_id)
        logger.warning("partners search msg id: %s", int(prev_partners_msg_id))

        await bot.edit_message_text(
            text = msg1.format(nickname=partners_nickname, about=partners_about),
            chat_id=request.user_id,
            message_id=prev_users_search_msg_id.decode(),
            reply_markup=create_start_chat_button(lang_code=lang_code1, link=link1),
            parse_mode=ParseMode.HTML,
        )

        await bot.edit_message_text(
            text=msg2.format(nickname=users_nickname, about=users_about),
            chat_id=request.partner_id,
            message_id=prev_partners_msg_id.decode(),
            reply_markup=create_start_chat_button(lang_code=lang_code2, link=link2),
            parse_mode=ParseMode.HTML,
        )


    return {"status": "notification_sent"}
