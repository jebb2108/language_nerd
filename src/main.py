import asyncio
from datetime import timedelta
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from dependencies import get_redis

from src.config import config
from src.logconf import opt_logger as log
from src.middlewares.quiz_middleware import QuizMiddleware
from src.middlewares.rate_limit_middleware import RateLimitMiddleware
from src.routers import router as main_router

logger = log.setup_logger("main")

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

    # Инициализация бота
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    redis = await get_redis()
    storage = RedisStorage(
        await redis.get_redis_client(),
        state_ttl=timedelta(minutes=10),
        data_ttl=timedelta(minutes=60)
    )

    # Инициализация диспетчера
    disp = Dispatcher(storage=storage)

    # Инициализация Middlewares
    await init_resources()

    #  Регистрация middleware -> Messages
    disp.message.middleware(quiz_middleware)
    disp.message.middleware(rate_limit_middleware)
    # Callbacks
    disp.callback_query.middleware(quiz_middleware)

    # Добавление роутеров
    disp.include_router(main_router)

    try:
        logger.info("Starting main tg-src-service (polling)…")
        await disp.start_polling(bot)

    finally:
        # Корректное завершение
        await bot.close()


if __name__ == "__main__":
    asyncio.run(run())
