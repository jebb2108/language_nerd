import sys
import logging
from aiogram.types import CallbackQuery, Message
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import LOG_CONFIG # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='message_mgr')


class QuizMiddleware:
    """Middleware для управления сообщениями quiz"""

    def __init__(self):
        self.quiz_messages = defaultdict(list)
        self.quiz_active = defaultdict(bool)  # Отслеживание активных quiz по chat_id

    async def __call__(self, handler, event, data):
        # Обрабатываем входящие сообщения и callback-запросы
        if isinstance(event, CallbackQuery):
            await self.process_callback_query(event)
        if isinstance(event, Message) and event.from_user.is_bot:
            await self.process_bot_message(event)

        return await handler(event, data)

    async def process_callback_query(self, callback_query: CallbackQuery):
        callback_data = callback_query.data
        chat_id = callback_query.message.chat.id

        # Ключи, которые запускают или являются частью quiz
        quiz_keys = ["camefrom_", "start_report:", "quiz:"]
        end_keys = ['action_confirm', 'end_quiz']

        # Если это начало quiz, помечаем чат как активный
        if any(callback_data.startswith(key) for key in quiz_keys):
            self.quiz_active[chat_id] = True
            if callback_query.message.message_id not in self.quiz_messages[chat_id]:
                self.quiz_messages[chat_id].append(callback_query.message.message_id)

        # Если quiz завершается, удаляем все сообщения
        elif callback_data in end_keys:
            await self.cleanup_quiz_messages(chat_id, callback_query.bot)
            self.quiz_active[chat_id] = False

    async def process_bot_message(self, message: Message):
        chat_id = message.chat.id

        # Если в чате активен quiz, сохраняем все сообщения от бота
        if self.quiz_active.get(chat_id, False):
            if message.message_id not in self.quiz_messages[chat_id]:
                self.quiz_messages[chat_id].append(message.message_id)

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