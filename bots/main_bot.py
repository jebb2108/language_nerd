import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from web_launcher import start_web_app
from config import logger, BOT_TOKEN_MAIN
from middlewares.resources_middleware import ResourcesMiddleware
from middlewares.rate_limit_middleware import RateLimitMiddleware
from routers import router as main_router


# Создаем хранилище состояний в оперативной памяти
storage = MemoryStorage()

async def run():
    """Запуск бота и веб-сервера в одном event loop"""

    # Инициализация диспетчера
    disp = Dispatcher(storage=storage)
    # Инициализация бота

    bot = Bot(token=BOT_TOKEN_MAIN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    resources = ResourcesMiddleware()
    pool = await resources.on_startup()

    # Запуск веб-сервера
    web_runner = await start_web_app(pool)

    disp.message.middleware(resources)
    disp.callback_query.middleware(resources)
    disp.inline_query.middleware(resources)
    disp.message.middleware(RateLimitMiddleware())

    # Добавление роутеров
    disp.include_router(main_router)

    try:
        logger.info("Starting main bot (polling)…")
        await disp.start_polling(bot)
    finally:
        # Корректное завершение
        await bot.session.close()
        await web_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(run())