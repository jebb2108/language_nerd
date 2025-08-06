import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from web_launcher import start_web_app
from config import logger, Resources, BOT_TOKEN_MAIN
from di import ResourcesMiddleware
from routers import router as main_router

# Создаем хранилище состояний в оперативной памяти
storage = MemoryStorage()

async def run():
    """Запуск бота и веб-сервера в одном event loop"""
    # Инициализация глобальных ресурсов
    resources = Resources()
    await resources.init()

    # Запуск веб-сервера
    web_runner = await start_web_app(resources.db_pool)

    dp = Dispatcher(storage=storage)

    # Регистрируем middleware и передаем ресурсы
    resources_middleware = ResourcesMiddleware(resources)
    dp.message.middleware(resources_middleware)
    dp.callback_query.middleware(resources_middleware)

    # Сохраняем resources в диспетчере
    dp["resources"] = resources

    dp.update.middleware(resources_middleware)  # <-- важно!

    # Инициализация бота
    bot = Bot(token=BOT_TOKEN_MAIN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp.include_router(main_router)

    try:
        logger.info("Starting main bot (polling)…")
        await dp.start_polling(bot)
    finally:
        # Корректное завершение
        await bot.session.close()
        await web_runner.cleanup()
        await resources.close()


if __name__ == "__main__":
    asyncio.run(run())