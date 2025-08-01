import os
import sys
import asyncpg
import logging
from aiohttp import ClientSession

from db_cmds import db_pool as pool

# Настройка логирования
logger = logging.getLogger(name=__name__)
logger.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# Конфигурация ботов
BOT_TOKEN_MAIN = os.getenv('BOT_TOKEN_MAIN')
BOT_TOKEN_PARTNER = os.getenv("BOT_TOKEN_PARTNER")

# Конфигурация API
AI_API_URL = os.getenv('OPENAI_API_URL')
AI_API_KEY = os.getenv('OPENAI_API_KEY')

# Конфигурация БД
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "telegram_bot")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

# Глобальные ресурсы
db_pool = None
session = None

async def init_global_resources():
    global session, db_pool
    # Инициализация HTTP сессии
    db_pool = await pool.init()
    logger.info("Database connection initialized")
    session = ClientSession()


async def close_global_resources():
    global db_pool, session
    if db_pool:
        await db_pool.close()
    if session:
        await session.close()