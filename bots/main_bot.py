"""
ТЕЛЕГРАМ-БОТЫ: ГЛАВНЫЙ БОТ И БОТ-ПАРТНЕР

1. Основной бот (Main Bot) - предоставляет меню и информацию
2. Бот-партнер (Partner Bot) - позволяет общаться с другими пользователем

Оба бота запускаются параллельно друг другу из разных файлов
"""
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from web_launcher import start_web_app
from routers import router as main_router
from config import (
    init_global_resources,
    close_global_resources,
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
    db_pool, session = await init_global_resources()
    # Запуск веб-сервера
    web_runner = await start_web_app(db_pool)
    # Получение токена бота
    from config import BOT_TOKEN_MAIN
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
        await close_global_resources()


if __name__ == "__main__":
    asyncio.run(run())