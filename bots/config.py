import os
import sys
import asyncpg
import logging
from aiohttp import ClientSession
from dotenv import load_dotenv

load_dotenv(".env")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN_MAIN = os.getenv('BOT_TOKEN_MAIN')
BOT_TOKEN_PARTNER = os.getenv('BOT_TOKEN_PARTNER')

AI_API_URL = os.getenv('AI_API_URL')
AI_API_KEY = os.getenv('AI_API_KEY')
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "telegram_bot")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))


class Resources:
    """Класс для управления ресурсами приложения"""

    def __init__(self):
        self.db_pool = None
        self.session = None

    async def init(self):
        """Инициализация ресурсов"""
        try:
            # Создаем пул подключений к БД
            self.db_pool = await asyncpg.create_pool(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                min_size=3,
                max_size=10
            )

            # Инициализируем структуру БД
            from db_cmds import Database
            db = Database(self.db_pool)
            await db.init()

            # Создаем HTTP-сессию
            self.session = ClientSession()
            logger.info("Resources initialized successfully")
            return self
        except Exception as e:
            logger.error(f"Resource initialization failed: {e}")
            await self.close()
            raise

    async def close(self):
        """Корректное закрытие ресурсов"""
        errors = []
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                logger.info("HTTP session closed")
        except Exception as e:
            errors.append(f"Error closing HTTP session: {e}")

        try:
            if self.db_pool:
                await self.db_pool.close()
                logger.info("Database pool closed")
        except Exception as e:
            errors.append(f"Error closing database pool: {e}")

        if errors:
            logger.error(" | ".join(errors))