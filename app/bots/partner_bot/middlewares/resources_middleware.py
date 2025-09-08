import logging

import redis.asyncio as redis
import asyncio
from dataclasses import dataclass
from datetime import timedelta

from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject
from aiogram.fsm.storage.redis import RedisStorage
from aiohttp import ClientSession


from app.dependencies import get_db
from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="resources_middleware")


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
        self._lock = asyncio.Lock()
        self._initialized = False
        self._initialization_failed = False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        data.update(
            database=await get_db(),
            redis=self.redis,
            http_session=self.session,
        )
        return await handler(event, data)

    def access_memory(self, param: str = "storage"):
        return dict(
            {
                "storage": self.storage,
                "database": get_db,
            }
        ).get(param, None)

    async def initialize_resources(self, storage_state_ttl, storage_data_ttl):
        """Инициализация ресурсов с созданием экземпляра Database"""
        try:

            # Создаем клиент Redis с пулом подключений
            redis_pool = redis.ConnectionPool.from_url(url=config.REDIS_URL)
            self.redis = redis.Redis(connection_pool=redis_pool)

            # Создаем Redis storage переменную
            self.storage = RedisStorage(
                self.redis,
                state_ttl=timedelta(minutes=storage_state_ttl),
                data_ttl=timedelta(minutes=storage_data_ttl),
            )
            logger.debug(
                "Redis storage initialized. State TTL - %s min, Data TTL - %s min",
                storage_state_ttl,
                storage_data_ttl,
            )

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
            if self.redis:
                await self.redis.close()
                logger.debug("Redis pool closed")
        except Exception as e:
            errors.append(f"Redis pool close error: {e}")

        if errors:
            logger.error(" | ".join(errors))

    # Методы для интеграции с жизненным циклом aiogram
    async def on_startup(
        self, storage_state_ttl: int = 10, storage_data_ttl: int = 60
    ) -> None:
        """Предварительная инициализация при старте приложения"""
        try:
            async with self._lock:
                # Проверяем, не была ли уже выполнена инициализация
                if not self._initialized and not self._initialization_failed:
                    logger.debug("Starting resource initialization...")
                    await self.initialize_resources(storage_state_ttl, storage_data_ttl)
                    self._initialized = True
                    logger.debug("Resource initialization completed successfully")

        except Exception as e:
            self._initialization_failed = True
            logger.critical(f"Resource initialization failed: {e}", exc_info=True)

            # Закрываем ресурсы, если была частичная инициализация
            await self._safe_close()
            raise  # Пробрасываем исключение дальше, чтобы остановить приложение

        return

    async def on_shutdown(self):
        """Очистка ресурсов при остановке"""
        await self.session.close()
        await self.redis.aclose()
        await self.close()
