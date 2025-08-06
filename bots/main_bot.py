"""
ТЕЛЕГРАМ-БОТЫ: ГЛАВНЫЙ БОТ И БОТ-ПАРТНЕР

1. Основной бот (Main Bot) - предоставляет меню и информацию
2. Бот-партнер (Partner Bot) - позволяет общаться с другими пользователем

Оба бота запускаются параллельно друг другу из разных файлов
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from web_launcher import start_web_app
from config import (
    Resources,
    logger,
)

# Создаем хранилище состояний в оперативной памяти
storage = MemoryStorage()

"""
===== ЗАПУСК ВСЕЙ СИСТЕМЫ =====
"""

async def run():
    """Запуск бота и веб-сервера в одном event loop"""

    # Инициализация глобальных ресурсов
    resources = Resources()
    # Запуск веб-сервера
    web_runner = await start_web_app(resources.db_pool)
    # Получение токена бота и роутеров
    from config import BOT_TOKEN_MAIN
    from routers import router as main_router
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN_MAIN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.include_router(main_router)

    try:
        # Основной цикл работы
        await dp.start_polling(bot)
        logger.info("Starting main bot (polling)…")

    finally:
        # Корректное завершение
        await bot.session.close()
        await web_runner.cleanup()
        await resources.close()


if __name__ == "__main__":
    asyncio.run(run())