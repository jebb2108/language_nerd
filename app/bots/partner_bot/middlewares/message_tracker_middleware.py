import asyncio
from collections import defaultdict
from typing import Callable, Any, Dict, TYPE_CHECKING
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.dependencies import get_redis
from app.models import SentMessage
from config import config
from logging_config import setup_logger

if TYPE_CHECKING:
    from aiogram import Bot

logger = setup_logger('message_tracker', config.LOG_LEVEL)

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
            pass

        # Вызываем основной обработчик
        result = await handler(event, data)

        if isinstance(result, Message):
            await self.track_message(result)

        # Для перехвата ИСХОДЯЩИХ сообщений используем отдельную стратегию
        # Создаем задачу для мониторинга состояния после обработки
        # asyncio.create_task(self._post_process(event, data))

        return result


    async def track_message(self, message: Message):
        """Отслеживаем отправленные сообщения"""
        try:
            chat_id = message.chat.id
            message_id = message.message_id
            message_info = SentMessage(
                chat_id=chat_id,
                message_id=message_id,
                text=message.text or message.caption,
            )
            # Если это сообщение о начале поиска
            if message_info.text.startswith("🔍"):
                await self.start_search(message_info)

        except Exception as e:
            logger.error(f"Error in track_message: {e}")


    async def start_search(self, message_info: "SentMessage") -> None:
        """Начинаем отслеживание поиска"""
        chat_id = message_info.chat_id
        message_id =  message_info.message_id

        try:
            redis = await get_redis()
            # Сохраняем в Redis с TTL
            await redis.save_sent_message(
                chat_id,
                message_info,
                config.WAIT_TIMER
            )
            # Очищаем предыдущие сообщения поиска для этого чата
            await self.cleanup_previous_searches(chat_id, message_id)
            # Добавляем в отслеживаемые сообщения
            self.search_messages[chat_id].append(message_id)
            self.active_searches[chat_id] = True
            logger.info(f"Started tracking search: chat={chat_id}, message={message_id}")

        except Exception as e:
            logger.error(f"Error in start_search_handler: {e}")


    async def cleanup_previous_searches(self, chat_id: int, curr_mid):
        """Очищаем предыдущие сообщения поиска"""
        try:
            if chat_id in self.search_messages and self.search_messages[chat_id]:
                for message_id in self.search_messages[chat_id]:
                    # Рредактируем сообщение вместо удаления,
                    # чтобы сохранить историю переписки
                    if message_id != curr_mid:
                        await asyncio.sleep(0.5)
                        await self.bot.delete_message(chat_id, message_id)
                        self.search_messages[chat_id].remove(message_id)
                self.active_searches[chat_id] = False

        except Exception as e:
            logger.error(f"Error in cleanup_previous_searches: {e}")
