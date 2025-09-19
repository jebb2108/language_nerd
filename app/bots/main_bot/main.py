import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode
from typing import Optional

from app.bots.main_bot.api.web_launcher import start_web_app
from app.dependencies import get_db, get_redis
from config import LOG_CONFIG, config
from app.bots.main_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.main_bot.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.bots.main_bot.middlewares.quiz_middleware import QuizMiddleware

from app.api.ai_handler.ai_report_generator import generate_weekly_reports
from app.api.ai_handler.ai_quiz_sender import send_pending_reports

from routers import router as main_router

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="main_bot")

# Глобальная переменная с ресурсами бота
resources: Optional["ResourcesMiddleware"] = None
rate_limit_middleware: Optional["RateLimitMiddleware"] = None
quiz_middleware: Optional["QuizMiddleware"] = None


async def init_resources() -> None:
    global resources, rate_limit_middleware, quiz_middleware
    """Запуск глобальных ресурсов """
    # Аргументы к on_startup - время в минутах
    # Создаю менеджера сообщений
    resources = ResourcesMiddleware()
    rate_limit_middleware = RateLimitMiddleware()
    quiz_middleware = QuizMiddleware()
    await resources.on_startup()


def setup_scheduler(scheduler, bot, db) -> None:
    # Отправляет их каждому пользователю
    scheduler.add_job(
        lambda: send_pending_reports(bot, db),
        trigger=CronTrigger(
            day_of_week='sun',
            hour=12,
            minute=0,
            timezone=config.TZINFO
        ),
        id='sending_reports',
        replace_existing=True
    )


# noinspection PyUnresolvedReferences
async def run():
    """Запуск бота и веб-сервера в одном event loop"""

    await init_resources()
    redis = await get_redis(call_client=True)
    storage = RedisStorage(redis, state_ttl=10, data_ttl=60)

    # Инициализация диспетчера
    disp = Dispatcher(storage=storage)

    # Инициализация бота
    bot = Bot(
        token=config.BOT_TOKEN_MAIN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Инициализация БД
    db = await get_db()
    # Создаем планировщик задач
    scheduler = AsyncIOScheduler()
    # Подключаем задачи для планировщика
    setup_scheduler(scheduler, bot, db)
    # Запуск веб-сервера
    web_runner = await start_web_app(db)

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
        logger.info("Starting scheduler...")
        scheduler.start()
        logger.info("Starting main bot (polling)…")
        await disp.start_polling(bot)

    finally:
        # Корректное завершение
        scheduler.shutdown()
        await bot.session.close()
        await web_runner.cleanup()
        await resources.on_shutdown()


if __name__ == "__main__":
    asyncio.run(run())
