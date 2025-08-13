import sys
import logging
from typing import Union, Optional, List
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import LOG_CONFIG # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='message_mgr')


class MessageManager:
    def __init__(self, bot: Bot, state: FSMContext):
        self.bot = bot
        self.state = state

    async def send_message_with_save(
            self,
            chat_id: int,
            text: str,
            parse_mode: Optional[str] = None,
            reply_markup: Optional[types.InlineKeyboardMarkup] = None
    ) -> types.Message:
        """Отправляет сообщение, сохраняя его ID и удаляя предыдущий вопрос"""
        data = await self.state.get_data()

        # Отправляем новое сообщение
        sent = await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

        # Сохраняем данные
        msgs = data.get("messages_to_delete", [])
        msgs.append(sent.message_id)
        await self.state.update_data(
            last_question_id=sent.message_id,
            messages_to_delete=msgs
        )

        return sent

    async def delete_previous_messages(self, chat_id: int) -> None:
        """Удаляет все сообщения кроме последнего"""
        data = await self.state.get_data()
        messages = data.get("messages_to_delete", [])

        if not messages:
            return

        # Сохраняем последнее сообщение
        last_message = messages[-1]

        # Удаляем все кроме последнего
        for msg_id in messages[:-1]:
            try:
                await self.bot.delete_message(chat_id, msg_id)
            except Exception as e:
                logger.warning(f"Ошибка удаления сообщения {msg_id}: {e}")

        # Обновляем state
        await self.state.update_data(
            messages_to_delete=[last_message],
            last_question_id=last_message
        )