import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bots.main_bot.api.web_launcher import start_web_app
from config import LOG_CONFIG, config
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.bots.partner_bot.middlewares.quiz_middleware import QuizMiddleware

from routers import router as main_router

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="main_bot")

# Глобальная переменная с ресурсами бота
resources = None
quiz_middleware = None
rate_limit_middleware = None


async def init_resources() -> None:
    global resources, quiz_middleware, rate_limit_middleware
    """Запуск глобальных ресурсов """
    # Аргументы к on_startup - время в минутах
    # Создаю менеджера сообщений
    quiz_middleware = QuizMiddleware()
    resources = ResourcesMiddleware()
    rate_limit_middleware = RateLimitMiddleware()
    await resources.on_startup(10, 60)


# noinspection PyUnresolvedReferences
async def run():
    """Запуск бота и веб-сервера в одном event loop"""

    await init_resources()

    # Инициализация диспетчера
    disp = Dispatcher(storage=resources.access_memory())

    # Инициализация бота
    bot = Bot(
        token=config.BOT_TOKEN_MAIN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Запуск веб-сервера
    web_runner = await start_web_app(resources.access_memory("database"))

    # Регистрация middleware
    # Messages
    disp.message.middleware(resources)
    disp.message.middleware(rate_limit_middleware)
    disp.message.middleware(quiz_middleware)
    # Callbacks
    disp.callback_query.middleware(quiz_middleware)
    disp.callback_query.middleware(resources)
    # Inline buttons
    disp.inline_query.middleware(resources)

    # Добавление роутеров
    disp.include_router(main_router)

    try:
        logger.info("Starting main bot (polling)…")
        await disp.start_polling(bot)

    finally:
        # Корректное завершение
        await bot.session.close()
        await web_runner.cleanup()
        await resources.on_shutdown()


if __name__ == "__main__":
    asyncio.run(run())
