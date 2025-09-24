import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from asyncpg.pgproto.pgproto import timedelta

from app.bots.partner_bot.routers import router as main_router
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitMiddleware

from app.dependencies import get_redis

# Импорт функций БД
from config import config, LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="partner_bot")

# Глобальные переменные
resources: Optional["ResourcesMiddleware"] = None
rate_limit_middleware: Optional["RateLimitMiddleware"] = None


async def init_resources():
    """Инициализация глобальных ресурсов"""
    global resources, rate_limit_middleware
    resources = ResourcesMiddleware()
    rate_limit_middleware = RateLimitMiddleware()
    await resources.on_startup()


async def run():
    await init_resources()
    bot = Bot(
        token=config.BOT_TOKEN_PARTNER,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    redis = await get_redis(call_client=True)
    storage = RedisStorage(redis, state_ttl=timedelta(minutes=10), data_ttl=timedelta(minutes=60))
    disp = Dispatcher(storage=storage)

    disp.include_router(main_router)
    disp.message.middleware(resources)
    disp.callback_query.middleware(resources)
    disp.message.middleware(RateLimitMiddleware())


    try:

        logger.info("Starting partner bots (polling)…")
        await disp.start_polling(bot)

    finally:
        await bot.session.close()
        await resources.on_shutdown()


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(run())
