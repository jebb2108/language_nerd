from typing import TYPE_CHECKING
from app.dependencies import get_redis_client, get_db
from app.bots.partner_bot.translations import BUTTONS
from aiogram.types import Message
from aiogram.filters import Filter

if TYPE_CHECKING:
    from app.models import Language



class AnswerFilter(Filter):
    """Фильтр для проверки ответа пользователя"""
    def __init__(self, option: str) -> bool:
        super().__init__()
        self.option = option

    async def __call__(self, message: Message):
        lang_code = await self.get_lang_code(message.from_user.id)
        if self.option == "agreed":
            return message.text == BUTTONS["yes_to_dating"][lang_code]
        elif self.option == "disagreed":
            lang_code = await self.get_lang_code(message.from_user.id)
            return message.text == BUTTONS["no_to_dating"][lang_code]
        elif self.option == "cancelled":
            lang_code = await self.get_lang_code(message.from_user.id)
            return self.option == BUTTONS["cancel"][lang_code]


    @staticmethod
    async def get_lang_code(user_id: int) -> "Language":
        redis_client = await get_redis_client()
        r_lang_code = await redis_client.get(f"lang_code:{user_id}")
        if not r_lang_code:
            database = await get_db()
            data = await database.get_user_info(user_id)
            await redis_client.setex(
                f"lang_code:{user_id}", 900, data["lang_code"]
            )
            r_lang_code = await redis_client.get(f"lang_code:{user_id}")

        return r_lang_code