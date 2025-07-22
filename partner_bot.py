import asyncio
import sys
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv


# Импорт текстовых сообщений из отдельного файла (config.py)
from config import *
from db_cmds import *
from routers import router as main_router

# Загрузка переменных окружения ДОЛЖНА БЫТЬ ВЫЗВАНА
load_dotenv(""".env""")

bot_token = os.getenv("BOT_TOKEN_PARTNER")

storage = MemoryStorage()
"""
=============== ЗАПУСК ВСЕЙ СИСТЕМЫ ===============
"""

async def run():
    """
    Запускает одного бота
    Параметры:
    - bot_token: токен Telegram бота
    - router: маршрутизатор с обработчиками
    - storage: хранилище состояний (опционально)
    """

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    await init_db()

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp.include_router(main_router)

    logging.info("Starting partner bot (polling)…")
    await dp.start_polling(bot)

    # Закрываем соединение с БД при завершении
    await close_db()
    logging.info("Database connection closed")


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(run())