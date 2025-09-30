import asyncio
import logging
from collections import defaultdict
from typing import Callable, Any, Dict, TYPE_CHECKING
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.dependencies import get_redis, get_redis_client
from app.models import SentMessage

from config import LOG_CONFIG, config

if TYPE_CHECKING:
    from aiogram import Bot

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="message_tracker_middleware")

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
        asyncio.create_task(self._post_process(event, data))

        return result


    async def track_message(self, message: Message):
        """Отслеживаем отправленные сообщения"""
        try:
            chat_id = message.chat.id
            message_id = message.message_id



            message_info = SentMessage(
                message_id=message_id,
                chat_id=chat_id,
                text=message.text or message.caption,
            )

            # Если это сообщение о начале поиска
            if message_info.text.startswith("🔍"):
                await self.start_search(chat_id, message_id, message_info)

        except Exception as e:
            logger.error(f"Error in track_message: {e}")






    async def _post_process(self, event: Any, data: Dict[str, Any]):
        """Пост-обработка после завершения хендлера"""

        # Даем время на отправку сообщений
        await asyncio.sleep(0.5)

        print(data)


        if isinstance(event, Message):
            await self.check_webapp_buttons(event)





    async def _check_chat_state(self, chat_id: int, bot: "Bot"):
        """Проверяем состояние чата и обновляем сообщения"""
        if chat_id in self.search_messages:
            # Ваша логика проверки TTL и WebApp кнопок
            redis = await get_redis()
            key = f"search_message:{chat_id}"
            if not await redis.exists(key):
                await self.cleanup_previous_searches()
        logger.warning(f"There is this active search going on: {self.search_messages[chat_id]}")



    async def start_search(self, chat_id: int, message_id: int, message_info: "SentMessage") -> None:
        """Начинаем отслеживание поиска"""
        try:
            redis = await get_redis()
            key = f"search_message:{message_id}"
            # Сохраняем в Redis с TTL
            await redis.save_sent_message(
                key,
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



    async def finish_search(self, message: Message):
        """Завершаем поиск и редактируем сообщения"""
        redis_client = await get_redis_client()
        q = await redis_client.lrange("sent_messages", 0, -1)
        q = [msg.decode() for msg in q]
        tp = config.SEARCH_COMPLETED_MESSAGE_TYPE
        web_appeeared: dict = next([msg for msg in q if msg.get("message_type") == tp], None)
        if web_appeeared:
            chat_id = web_appeeared.get("chat_id")
            msg_id = web_appeeared.get("message_id")
            self.




        # for indx, message_id in enumerate(queue, 0):
        #     mid = message_id.decode()
        #     key = f"search_message:{mid}"
        #     m_data: dict = await redis_client.hgetall(key)
        #     if m_data.get("web_info") == 1:






    async def cleanup_previous_searches(self, chat_id: int, curr_mid):
        """Очищаем предыдущие сообщения поиска"""
        try:
            if chat_id in self.search_messages and self.search_messages[chat_id]:
                for message_id in self.search_messages[chat_id]:
                    # Рредактируем сообщение вместо удаления,
                    # чтобы сохранить историю переписки
                    if message_id != curr_mid:

                        await self.bot.delete_message(chat_id, message_id)
                        self.search_messages[chat_id].remove(message_id)

                self.active_searches[chat_id] = False

        except Exception as e:
            logger.error(f"Error in cleanup_previous_searches: {e}")


    async def check_webapp_buttons(self, message: Message) -> None:
        """Проверяем WebApp кнопки (партнер найден)"""

        chat_id = message.chat.id

        if not self.active_searches.get(chat_id):
            return

        has_webapp = False
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                if hasattr(button, 'web_app') and button.web_app:
                    has_webapp = True
                    break
            if has_webapp:
                break

        if has_webapp:
            # Завершаем поиск
            await self.finish_search(message)
