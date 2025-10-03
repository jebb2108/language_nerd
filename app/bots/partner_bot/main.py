import asyncio
from typing import Optional

from logging_config import opt_logger as log

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from asyncpg.pgproto.pgproto import timedelta

from app.bots.partner_bot.middlewares.message_tracker_middleware import (
    MessageTrackerMiddleware,
)
from app.bots.partner_bot.routers import router as main_router
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitMiddleware

from app.dependencies import get_redis_client, get_partner_bot

# Импорт функций БД
from config import config

logger = log.setup_logger("partner_bot", config.LOG_LEVEL)

# Глобальные переменные
rate_limit_middleware: Optional["RateLimitMiddleware"] = None
message_tracker_middleware: Optional["MessageTrackerMiddleware"] = None


async def init_resources(bot):
    """Инициализация глобальных ресурсов"""
    global rate_limit_middleware, message_tracker_middleware
    message_tracker_middleware = MessageTrackerMiddleware(bot)
    rate_limit_middleware = RateLimitMiddleware()


async def run():

    bot = await get_partner_bot()

    redis = await get_redis_client()
    storage = RedisStorage(
        redis, state_ttl=timedelta(minutes=10), data_ttl=timedelta(minutes=60)
    )
    disp = Dispatcher(storage=storage)

    await init_resources(bot)

    disp.include_router(main_router)
    disp.message.outer_middleware(message_tracker_middleware)
    disp.callback_query.outer_middleware(message_tracker_middleware)
    disp.message.middleware(RateLimitMiddleware())

    try:
        logger.info("Starting partner bots (polling)…")
        await disp.start_polling(bot)

    finally:
        await bot.close()


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(run())
