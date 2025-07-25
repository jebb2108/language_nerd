from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

class IsBotFilter(BaseFilter):
    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    async def __call__(self, update: Message | CallbackQuery, bot: Bot) -> bool:
        return bot.token == self.bot_token