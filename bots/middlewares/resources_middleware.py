import logging
import sys
import asyncio
import asyncio_redis
from dataclasses import dataclass

import asyncpg
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject
from aiohttp import ClientSession

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DB_CONFIG, REDIS_CONFIG, LOG_CONFIG # noqa
from utils.database import Database  # Импортируем ваш класс DB # noqa\

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='resources_middleware')

@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

class ResourcesMiddleware(BaseMiddleware):
    """Middleware для управления ресурсами"""

    def __init__(self):
        super().__init__()
        self.db_config = DBConfig(**DB_CONFIG)
        self._lock = asyncio.Lock()
        self._initialized = False
        self._initialization_failed = False
        self.db_pool = None
        self.redis_pool = None

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:

        if not self._initialized and not self._initialization_failed:
            async with self._lock:
                if not self._initialized and not self._initialization_failed:
                    try:
                        await self.initialize_resources()
                        self._initialized = True
                    except Exception as e:
                        self._initialization_failed = True
                        logger.critical(f"Resource init failed: {e}")
                        raise

        data.update(
            database=self.db,
            redis=self.redis_pool,
            http_session=self.session,
        )
        return await handler(event, data)


    async def initialize_resources(self):
        """Инициализация ресурсов с созданием экземпляра Database"""
        try:
            # Создаем пулы подключений к БД и Redis
            self.db_pool = await asyncpg.create_pool(**self.db_config.__dict__)
            self.redis_pool = await asyncio_redis.Pool.create(**REDIS_CONFIG)

            # Создаем экземпляр класса Database
            self.db = Database(self.db_pool)
            logger.debug("Database initialized")

            # Инициализация других ресурсов
            self.session = ClientSession()
            logger.debug("HTTP session initialized")

        except Exception as e:
            logger.error(f"Resource initialization failed: {e}")
            await self._safe_close()
            raise

    async def close(self):
        """Закрытие всех ресурсов"""
        if self._initialized:
            await self._safe_close()
            self._initialized = False
            logger.debug("All resources closed")


    async def _safe_close(self):
        """Безопасное закрытие с обработкой ошибок"""
        errors = []

        # Закрываем HTTP-сессию и пул подключений
        # Закрываем пул подключений
        try:
            if self.db_pool and not self.db_pool._closed:
                await self.db_pool.close()
                logger.debug("Database pool closed")
            if self.redis_pool and not self.redis_pool._closed:
                await self.redis_pool.close()
                logger.debug("Redis pool closed")
        except Exception as e:
            errors.append(f"Database || Redis pool close error: {e}")

        if errors:
            logger.error(" | ".join(errors))

    # Методы для интеграции с жизненным циклом aiogram
    async def on_startup(self):
        """Предварительная инициализация при старте приложения"""
        try:
            async with self._lock:
                # Проверяем, не была ли уже выполнена инициализация
                if not self._initialized and not self._initialization_failed:
                    logger.debug("Starting resource initialization...")
                    await self.initialize_resources()
                    self._initialized = True
                    logger.debug("Resource initialization completed successfully")

        except Exception as e:
            self._initialization_failed = True
            logger.critical(f"Resource initialization failed: {e}", exc_info=True)

            # Закрываем ресурсы, если была частичная инициализация
            await self._safe_close()
            raise  # Пробрасываем исключение дальше, чтобы остановить приложение

        return self.db

    async def on_shutdown(self):
        """Очистка ресурсов при остановке"""
        await self.close()
        await self.session.close()
