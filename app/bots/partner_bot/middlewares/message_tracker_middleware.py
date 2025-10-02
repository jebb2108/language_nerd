import asyncio
from collections import defaultdict
from typing import Callable, Any, Dict, TYPE_CHECKING
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from app.dependencies import get_redis
from app.services.redis import RedisService
from config import config
from logging_config import opt_logger as log

if TYPE_CHECKING:
    from aiogram import Bot

logger = log.setup_logger('message_tracker', config.LOG_LEVEL)

class MessageTrackerMiddleware(BaseMiddleware):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.edited_messages = defaultdict(list)
        self.search_messages = defaultdict(list)
        self.active_searches = defaultdict(bool)

    async def __call__(
        self, handler: Callable, event: Any, data: Dict[str, Any]
    ) -> Any:

        # Обрабатываем ВХОДЯЩИЕ события ДО handler
        if isinstance(event, CallbackQuery):
            # await self.track_callback(event)
            logger.debug(f"Message deemed callable b4 processing")
            pass

        # Вызываем основной обработчик
        result = await handler(event, data)


        if isinstance(result, Message):
            redis = await get_redis()
            logger.debug(f"Post process of message %s", result.message_id)
            await self.track_message(result, redis)

        # Для перехвата ИСХОДЯЩИХ сообщений используем отдельную стратегию
        # Создаем задачу для мониторинга состояния после обработки
        # asyncio.create_task(self._post_process(event, data))

        return result


    async def track_message(self, message: Message, redis: "RedisService"):
        """Отслеживаем отправленные сообщения"""
        try:
            # Если это сообщение о начале поиска партнера
            if message.text.startswith("🔍"):
                await self.start_search(message, redis)

        except Exception as e:
            logger.error(f"Error in track_message: {e}")


    async def start_search(self, message: "Message", redis: "RedisService") -> None:
        """Начинаем отслеживание поиска"""
        cid = message.chat.id
        mid =  message.message_id
        # Добавляем в отслеживаемые сообщения
        self.active_searches[cid] = True
        # Сохраняем в Redis с TTL
        await redis.mark_msg_as_search(message)
        await redis.save_sent_message(message)
        # Очищаем предыдущие сообщения поиска для этого чата
        await self.cleanup_previous_searches(cid, redis)
        res = await redis.get_search_message_id(cid)
        logger.info(f"Started tracking search: chat={cid}, message={mid} -> {res}")


    async def cleanup_previous_searches(self, cid: int, redis: "RedisService") -> None:
        """Очищаем предыдущие сообщения поиска"""
        logger.debug("Starting to clean old messages ...")
        # Ивзлекаем уникальные ID из очереди сообщений
        for indx in await redis.get_sent_queue(cid):
            if self.active_searches[cid] and not await redis.check_search_msg(cid, indx):

                try:
                    await self.bot.delete_message(cid, int(indx))

                except TelegramBadRequest:
                    logger.debug("User deleted this message %s on their own", indx)

                else:
                    logger.debug("This message %s deleted", indx)

                await redis.delete_msg_from_queue(cid, indx)

            # Это может происходить только (!) при нажатии Cancel
            elif self.active_searches[cid] and await redis.check_search_msg(cid, indx):
                logger.debug("User %s canceled search. Stopped on msg %s", cid, indx)
                self.active_searches[cid] = False

        logger.debug("Stopped cleaning old messages")