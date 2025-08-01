# shared_resources.py
import os
from dotenv import load_dotenv
import asyncpg
import aiohttp

load_dotenv(".env")

from db_cmds import db_pool as pool

# Конфигурация
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN_MAIN')
AI_API_URL = os.getenv('OPENAI_API_URL')
AI_API_KEY = os.getenv('OPENAI_API_KEY')

# Глобальные ресурсы
db_pool = pool.init()
session = None

async def init_global_resources():
    global db_pool, session
    # Инициализация HTTP сессии
    session = aiohttp.ClientSession()


async def close_global_resources():
    global db_pool, session
    if db_pool:
        await db_pool.close()
    if session:
        await session.close()