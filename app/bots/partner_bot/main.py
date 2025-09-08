import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from routers import router as main_router
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitMiddleware

from app.bots.partner_bot.api.chat_launcher import start_server

# Импорт функций БД
from config import config, LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="partner_bot")

# Глобальные переменные
resources: Optional["ResourcesMiddleware", None] = None
rate_limit_middleware: Optional["RateLimitMiddleware", None] = None


async def init_resources():
    """Инициализация глобальных ресурсов"""
    global resources, rate_limit_middleware
    resources = ResourcesMiddleware()
    rate_limit_middleware = RateLimitMiddleware()
    await resources.on_startup(10, 10)


async def run():
    await init_resources()
    bot = Bot(
        token=config.BOT_TOKEN_PARTNER,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    disp = Dispatcher(storage=resources.access_memory())

    disp.include_router(main_router)
    disp.message.middleware(resources)
    disp.callback_query.middleware(resources)
    disp.message.middleware(RateLimitMiddleware())

    server = await start_server(resources.redis)

    try:
        logger.info("Starting partner bots (polling)…")
        await disp.start_polling(bot)

    finally:
        await bot.session.close()
        await resources.on_shutdown()
        await server.cleanup()


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(run())
