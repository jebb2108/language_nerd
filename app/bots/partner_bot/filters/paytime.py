from datetime import datetime, timedelta
from app.dependencies import get_db, get_redis_client
from logging_config import opt_logger as log
from typing import TYPE_CHECKING, Union
from config import config

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery,  Message


logger = log.setup_logger("paytime", "debug")

async def paytime(callback: Union["CallbackQuery", "Message"]):
    """ Проверяет, не истекла ли подписка пользователя """
    user_id = callback.from_user.id
    db = await get_db()
    redis_client = await get_redis_client()
    logger.debug(f"Проверка подписки для пользователя {user_id}")
    due_to = await redis_client.get(f"user_paid:{user_id}")
    if due_to and datetime.fromisoformat(due_to) > datetime.now():
            return True
    elif due_to := await db.get_users_due_to(user_id):
        if due_to > datetime.now():
            await redis_client.setex(f"user_paid:{user_id}", timedelta(hours=2), due_to.isoformat())
            return True

    return False