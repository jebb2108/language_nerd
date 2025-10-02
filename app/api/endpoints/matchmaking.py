from typing import TYPE_CHECKING
from aiogram.enums import ParseMode

from fastapi import APIRouter, Depends, HTTPException

from app.models import UserMatchResponse
from app.services.rabbitmq import RabbitMQService
from app.dependencies import get_rabbitmq, get_db, get_redis
from app.models.chat_models import UserMatchRequest
from app.bots.partner_bot.keyboards.inline_keyboards import create_start_chat_button
from app.bots.partner_bot.translations import MESSAGES
from app.validators.tokens import create_token
from config import config
from logging_config import opt_logger as log

if TYPE_CHECKING:
    from aiogram.types import Message

logger = log.setup_logger('endpoints', config.LOG_LEVEL)


router = APIRouter(prefix="/api")


@router.post("/match")
async def request_match(
    request: "UserMatchRequest",
    rabbitmq: "RabbitMQService" = Depends(get_rabbitmq),
    db=Depends(get_db),
):
    logger.info(
        f"Получен запрос на поиск партнера для пользователя {request.user_id}"
    )
    # Проверяем пользователя в БД
    user = await db.check_user_exists(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
    if is_searching: await redis.add_to_queue(request)
    # Отправляем запрос в очередь
    await rabbitmq.publish_message(request.model_dump())
    return {"status": "user added to queue"}


@router.post("/timed_out")
async def exit_match(data: "UserMatchResponse", db=Depends(get_db), redis=Depends(get_redis)):
    user_id = data.user_id
    lang_code = data.lang_code
    user = await db.check_user_exists(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from aiogram import Bot
    bot = Bot(token=config.BOT_TOKEN_PARTNER)
    curr_msg = await redis.get_search_message_id(user_id)

    await bot.edit_message_text(
        text=MESSAGES["timed_out"][lang_code],
        chat_id=user_id,
        message_id=curr_msg.decode(),
        reply_markup=None,
        parse_mode=ParseMode.HTML,
    )



@router.post("/cancel")
async def cancel_match(
    request: UserMatchRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    # Проверяем пользователя в БД
    user = await db.check_user_exists(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.debug(
        f"User ID: {request.user_id}, "
        f"criteria: {request.criteria}, "
        f"gender: {request.gender},"
        f"lang_code: {request.lang_code}"
    )

    # Отправляем сообщение в очередь
    await rabbitmq.publish_message(request.model_dump())
    await redis.remove_from_queue(request.user_id)
    return {"status": "User deleted from queue"}


@router.post("/notify")
async def notify_users_re_match(
    request: dict, db=Depends(get_db), redis=Depends(get_redis)
):

    room_id = request["room_id"]
    user_data = request["user"]
    partner_data = request["partner"]

    user_id = int(user_data["user_id"])
    partner_id = int(partner_data["user_id"])

    link = "https://chat.lllang.site/enter/{room_id}?token={token}"

    user_profile = await db.get_all_user_info(user_id)
    partner_profile = await db.get_all_user_info(partner_id)
    # Ссылки для подключения
    user_link = link.format(
        room_id=room_id, token=await create_token(user_id, room_id)
    )
    partner_link = link.format(
        room_id=room_id, token=await create_token(partner_id, room_id)
    )
    # Никнеймы, видимые партнеру
    user_nickname = user_profile.get("prefered_name")
    partner_nickname = partner_profile.get("prefered_name")
    # Извлекаю описание пользователю
    about_user = user_profile.get("about")
    about_partner = partner_profile.get("about")
    # Создаю сообщения
    user_msg = MESSAGES["match_found"][user_data.get("lang_code")]
    partner_msg = MESSAGES["match_found"][partner_data.get("lang_code")]

    prev_users_msg_id = await redis.get_search_message_id(user_id)
    prev_partners_msg_id = await redis.get_search_message_id(partner_id)

    from aiogram import Bot

    bot = Bot(token=config.BOT_TOKEN_PARTNER)

    try:
        await bot.edit_message_text(
            text=user_msg.format(nickname=partner_nickname, about=about_partner),
            chat_id=user_id,
            message_id=prev_users_msg_id.decode(),
            reply_markup=create_start_chat_button(
                # Отправляем сообщение с клавиатурой
                # на языке пользователя со ссылкой
                lang_code=user_data.get("lang_code"), link=user_link
            ),
            parse_mode=ParseMode.HTML,
        )

        from aiogram import Bot
        await bot.edit_message_text(
            text=partner_msg.format(nickname=user_nickname, about=about_user),
            chat_id=partner_id,
            message_id=prev_partners_msg_id.decode(),
            reply_markup=create_start_chat_button(
                # Отправляем сообщение с клавиатурой
                # на языке пользователя со ссылкой
                lang_code=partner_data["lang_code"], link=partner_link
            ),
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        logger.error(f"Error launching chat for users: {e}")
        raise HTTPException(
            status_code=500, detail="notification wasn't sent due to error"
        )

    finally:
        await bot.close()
        await redis.remove_from_queue(user_id)
        await redis.remove_from_queue(partner_id)
        return {"status": "notification_sent"}
