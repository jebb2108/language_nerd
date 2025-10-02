import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message
from asyncpg.pgproto.pgproto import timedelta

from pathlib import Path

from config import config
from logging_config import opt_logger as log

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bots.partner_bot.utils.async_timed_queue import AsyncTimedQueue

logger = log.setup_logger('rate_limit_middleware', config.LOG_LEVEL)


@dataclass(frozen=False)
class RateLimitInfo:
    """Отдельный класс для хранения информации
    о количестве сообщений и времени первого сообщения пользователя."""

    # Упрозает написание кода, позволяя не писать
    # магичесие методы e.g. __init__, __repr__, __eq__

    message_count: int
    last_message_time: datetime


class RateLimitMiddleware(BaseMiddleware):
    """Класс, который проверяет количество отправленных сообщений
    от пользователя и блокирует отправку сообщений бота, если лимит превышен"""

    def __init__(
        self,
        limit: int = 15,
        time_interval: timedelta = timedelta(seconds=30),
    ):
        self.rate_limit = limit
        self.time_interval = time_interval

        # Создаем словарь для хранения очередей

        # При обращении к отсутствующему ключу
        # (например, self.processed_messages[123])
        # вызывается лямбда-функция.

        # Она создает новый экземпляр AsyncTimedQueue,
        # передавая в конструктор параметр time_interval (объект timedelta).

        self.processed_messages = defaultdict[
            int, AsyncTimedQueue[datetime]
        ](  # типизация словаря
            lambda: AsyncTimedQueue(time_interval)  # Фабрика значений (экземпляры)
        )

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:

        user_id = event.from_user.id
        current_dt = datetime.now()
        processed_messages = self.processed_messages[user_id]
        count: int = await processed_messages.get_len()
        if count > self.rate_limit:
            logger.info("Skip user %s message", user_id)
            return

        await processed_messages.push(current_dt)
        count = await processed_messages.get_len()
        if count > self.rate_limit:
            logger.info("Skip user %s message (new)", user_id)
            return
        if count == self.rate_limit:
            logger.info("Sending last message to user %s before rate limit", user_id)
            await event.reply(
                text="You're sending too many messages. Please cool down for a while",
            )
            return

        data.update(
            rate_limit_info=RateLimitInfo(
                message_count=count,
                last_message_time=await processed_messages.peek(),
            ),
        )

        return await handler(event, data)
