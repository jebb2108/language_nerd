from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config


class PartnerBot:

    def __init__(self):
        self.bot = None
        self.initialized = False

    def get_bot(self):
        return self.bot

    async def connect(self):
        self.bot = Bot(
            token=config.BOT_TOKEN_PARTNER,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    async def close(self):
        await self.bot.close()


partner_bot = PartnerBot()
