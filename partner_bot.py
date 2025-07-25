import sys
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv

# Загрузка переменных окружения ДОЛЖНА БЫТЬ ВЫЗВАНА
load_dotenv(""".env""")


# Импорт текстовых сообщений из отдельного файла (config.py)
from db_cmds import *
from routers import router as main_router

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

    await db_pool.init()

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp.include_router(main_router)

    logging.info("Starting partner bot (polling)…")
    await dp.start_polling(bot)

    # Закрываем соединение с БД при завершении
    await db_pool.close()
    logging.info("Database connection closed")


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(run())