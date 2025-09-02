import sys
import logging
from aiogram.types import CallbackQuery, Message
from collections import defaultdict

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LOG_CONFIG  # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='message_mgr')


class QuizMiddleware:
    """ Middleware для менеджера сообщений """
    def __init__(self):
        self.quiz_messages = defaultdict(list)

    async def __call__(self, handler, event, data):
        # Обрабатываем как callback query, так и обычные сообщения
        if isinstance(event, CallbackQuery):
            await self.process_callback_query(event)
        elif isinstance(event, Message):
            await self.process_message(event)

        return await handler(event, data)

    async def process_callback_query(self, callback_query: CallbackQuery):
        callback_data = callback_query.data
        chat_id = callback_query.message.chat.id
        message_id = callback_query.message.message_id
        keys = ["camefrom_", "start_report:", "quiz:"]

        for key in keys:
            if callback_data.startswith(key):
                if message_id not in self.quiz_messages[chat_id]:
                    self.quiz_messages[chat_id].append(message_id)
                break  # Прерываем после первого совпадения

        if callback_data in ['action_confirm', 'end_quiz']:
            # Не добавляем текущий message_id повторно
            message_ids = self.quiz_messages.get(chat_id, [])

            # Удаляем все сообщения из списка
            for mid in message_ids:
                try:
                    await callback_query.bot.delete_message(chat_id, mid)
                except Exception as e:
                    logger.error(f"Ошибка при удалении сообщения {mid}: {e}")

            # Очищаем список для чата
            self.quiz_messages[chat_id] = []

    async def process_message(self, message: Message):
        # Сохраняем message_id сообщений, отправленных ботом во время квиза
        chat_id = message.chat.id
        message_id = message.message_id

        # Проверяем, является ли сообщение частью квиза
        if (message.reply_markup and
                hasattr(message.reply_markup, 'inline_keyboard') and
                any(button.callback_data and button.callback_data.startswith("quiz:")
                    for row in message.reply_markup.inline_keyboard
                    for button in row)):

            if message_id not in self.quiz_messages[chat_id]:
                self.quiz_messages[chat_id].append(message_id)