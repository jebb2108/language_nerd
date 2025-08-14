import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Импорт текстовых сообщений из отдельного файла (translations.py)
from routers import router as main_router
from middlewares.resources_middleware import ResourcesMiddleware
from middlewares.rate_limit_middleware import RateLimitMiddleware

# Импорт функций БД
from config import BOT_TOKEN_PARTNER, LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='partner_bot')

storage = MemoryStorage()

"""
=============== ЗАПУСК ВСЕЙ СИСТЕМЫ ===============
"""


async def run():
    """
    Запускает одного бота
    Параметры:
    - bot_token: токен Telegram бота
    - router: маршрутизатор с обработчиками
    - storage: хранилище состояний (опционально)
    """

    bot = Bot(token=BOT_TOKEN_PARTNER, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    disp = Dispatcher(storage=storage) if storage else Dispatcher()

    resources = ResourcesMiddleware()
    db = await resources.on_startup()
    await db.initialize()

    disp.include_router(main_router)
    disp.message.middleware(resources)
    disp.callback_query.middleware(resources)
    disp.message.middleware(RateLimitMiddleware())

    logger.info("Starting partner bots (polling)…")
    await disp.start_polling(bot)


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(run())
