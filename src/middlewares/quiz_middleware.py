import logging
from collections import defaultdict

from aiogram.types import CallbackQuery

logger = logging.getLogger(name='message_mgr')


class QuizMiddleware:
    """Middleware для управления сообщениями quiz"""

    def __init__(self):
        self.quiz_messages = defaultdict(list)

    async def __call__(self, handler, event, data):
        # Обрабатываем входящие сообщения и callback-запросы
        if isinstance(event, CallbackQuery):
            await self.process_callback_query(event)

        return await handler(event, data)

    async def process_callback_query(self, callback_query: CallbackQuery):
        callback_data = callback_query.data
        chat_id = callback_query.message.chat.id

        # Ключи, которые запускают или являются частью quiz
        start_keys = ["start_report:", "quiz:"]
        end_keys = ['action_confirm', 'end_quiz']

        # Если это начало quiz, помечаем чат как активный
        if any(callback_data.startswith(key) for key in start_keys):
            if callback_query.message.message_id not in self.quiz_messages[chat_id]:
                self.quiz_messages[chat_id].append(callback_query.message.message_id)

        # Если quiz завершается, удаляем все сообщения
        elif callback_data in end_keys:
            await self.cleanup_quiz_messages(chat_id, callback_query.bot)

    async def cleanup_quiz_messages(self, chat_id: int, bot):
        """Удаляет все сообщения quiz в указанном чате"""
        message_ids = self.quiz_messages.get(chat_id, [])

        for mid in message_ids:
            try:
                await bot.delete_message(chat_id, mid)
            except Exception as e:
                logger.error(f"Ошибка при удалении сообщения {mid}: {e}")

        # Очищаем список сообщений для чата
        self.quiz_messages[chat_id] = []