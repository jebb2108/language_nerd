import sys
import logging
from aiogram.types import CallbackQuery
from collections import defaultdict

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LOG_CONFIG # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='message_mgr')


class QuizMiddleware:
    """ Middleware для менеджера сообщений """
    def __init__(self):
        self.quiz_messages = defaultdict(list)

    async def __call__(self, handler, event, data):

        # Проверяем, является ли событие callback query
        if isinstance(event, CallbackQuery):
            await self.process_callback_query(event)

        return await handler(event, data)

    async def process_callback_query(self, callback_query: CallbackQuery):

        callback_data = callback_query.data
        chat_id = callback_query.message.chat.id
        message_id = callback_query.message.message_id
        keys = ["camefrom_", "start_report:", "qiuz:", ]

        for key in keys:
            if callback_data.startswith(key):
                self.quiz_messages[chat_id].append(message_id)


        if callback_data == 'action_confirm' or callback_data == 'end_quiz':
            chat_id = callback_query.message.chat.id
            message_ids = self.quiz_messages.get(chat_id, [])
            message_ids.append(message_id)

            # Удаляем все сообщения из списка
            for mid in message_ids:
                try:
                    await callback_query.bot.delete_message(chat_id, mid)
                except Exception as e:
                    logger.error(f"Ошибка при удалении сообщения {mid}: {e}")


            # Очищаем список для чата
            self.quiz_messages[chat_id] = []