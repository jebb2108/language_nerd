from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Union

from app.dependencies import get_db, get_redis_client
from config import config
from logging_config import opt_logger as log

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

logger = log.setup_logger("paytime", "debug")


async def approved(callback: Union["CallbackQuery", "Message"]):
    """Проверяет, не истекла ли подписка пользователя"""
    user_id = callback.from_user.id
    db = await get_db()
    redis_client = await get_redis_client()

    # 1. Проверяем кэш в Redis
    due_to = await redis_client.get(f"user_paid:{user_id}")
    if due_to:
        due_date = datetime.fromisoformat(due_to)
        # Приводим к naive datetime если нужно
        if due_date.tzinfo is not None:
            due_date = due_date.replace(tzinfo=None)

        if due_date > datetime.now().replace(tzinfo=None):
            return True

    # 2. Проверяем базу данных
    due_to, is_active = await db.get_users_due_to(user_id)
    due_date_db = due_to.replace(tzinfo=None) if due_to else due_to
    if due_date_db > datetime.now(tz=config.TZINFO).replace(tzinfo=None):
        # Приводим к naive datetime
        if is_active:
            # Сохраняем в кэш как ISO строку без временной зоны
            await redis_client.setex(
                f"user_paid:{user_id}",
                timedelta(hours=2),
                due_date_db.isoformat()
            )

        return True

    return False