import asyncio
from logging_config import opt_logger as log

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode
from typing import Optional

from asyncpg.pgproto.pgproto import timedelta

from app.dependencies import get_redis_client
from config import config
from app.bots.main_bot.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.bots.main_bot.middlewares.quiz_middleware import QuizMiddleware

from routers import router as main_router

logger = log.setup_logger('main bot', config.LOG_LEVEL)

# Глобальная переменная с ресурсами бота
rate_limit_middleware: Optional["RateLimitMiddleware"] = None
quiz_middleware: Optional["QuizMiddleware"] = None


async def init_resources() -> None:
    global rate_limit_middleware, quiz_middleware
    """Запуск глобальных ресурсов """
    # Создаю менеджера сообщений
    rate_limit_middleware = RateLimitMiddleware()
    quiz_middleware = QuizMiddleware()

# noinspection PyUnresolvedReferences
async def run():
    """Запуск бота и веб-сервера в одном event loop"""

    await init_resources()
    redis = await get_redis_client()
    storage = RedisStorage(redis, state_ttl=timedelta(minutes=10), data_ttl=timedelta(minutes=60))

    # Инициализация диспетчера
    disp = Dispatcher(storage=storage)

    # Инициализация бота
    bot = Bot(
        token=config.BOT_TOKEN_MAIN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    #  Регистрация middleware -> Messages
    disp.message.middleware(quiz_middleware)
    disp.message.middleware(rate_limit_middleware)
    # Callbacks
    disp.callback_query.middleware(quiz_middleware)

    # Добавление роутеров
    disp.include_router(main_router)

    try:
        logger.info("Starting main bot (polling)…")
        await disp.start_polling(bot)

    finally:
        # Корректное завершение
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
