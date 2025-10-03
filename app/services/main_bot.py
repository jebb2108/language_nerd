from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config


class MainBot:

    def __init__(self):
        self.bot = None
        self.initialized = False

    def get_bot(self):
        return self.bot

    def connect(self):
            self.bot = Bot(
                token=config.BOT_TOKEN_MAIN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

    async def close(self):
        await self.bot.close()



main_bot = MainBot()



