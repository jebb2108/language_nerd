import os
import sys
import asyncpg
import logging
from aiohttp import ClientSession

from dotenv import load_dotenv

load_dotenv(""".env""")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(name=__name__)

# Конфигурация ботов
BOT_TOKEN_MAIN = os.getenv('BOT_TOKEN_MAIN')
BOT_TOKEN_PARTNER = os.getenv("BOT_TOKEN_PARTNER")

# Конфигурация API
AI_API_URL = os.getenv('AI_API_URL')
AI_API_KEY = os.getenv('AI_API_KEY')

# Конфигурация БД
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "telegram_bot")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))

db_pool = None
session = None

async def init_global_resources():
    global db_pool, session
    pool = await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        min_size=5,
        max_size=20
    )

    from db_cmds import Database

    # Создаю пул и тут же его инициализирую
    db_pool = Database(pool)
    await db_pool.init()

    session = ClientSession()
    return db_pool, session


async def close_global_resources():
    if db_pool:
        await db_pool.close()
    if session:
        await session.close()