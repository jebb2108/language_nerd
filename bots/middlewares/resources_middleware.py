import sys
import asyncio
from dataclasses import dataclass

import asyncpg
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject
from aiohttp import ClientSession

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import db_config, logger # noqa
from utils.database import Database  # Импортируем ваш класс DB # noqa

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
        self.db_config = DBConfig(**db_config)
        self._lock = asyncio.Lock()
        self._initialized = False
        self._initialization_failed = False

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
            http_session=self.session,
        )

        return await handler(event, data)


    async def initialize_resources(self):
        """Инициализация ресурсов с созданием экземпляра Database"""
        try:
            # Создаем пул подключений
            pool = await asyncpg.create_pool(**self.db_config.__dict__)
            logger.info("Database pool created")

            # Создаем экземпляр класса Database
            self.db = Database(pool)
            logger.info("Database instance initialized")

            # Инициализация других ресурсов
            self.session = ClientSession()
            logger.info("HTTP session initialized")

        except Exception as e:
            logger.error(f"Resource initialization failed: {e}")
            await self._safe_close()
            raise

    async def close(self):
        """Закрытие всех ресурсов"""
        if self._initialized:
            await self._safe_close()
            self._initialized = False
            logger.info("All resources closed")


    async def _safe_close(self):
        """Безопасное закрытие с обработкой ошибок"""
        errors = []

        # Закрываем HTTP-сессию и пул подключений
        try:
            if not self.session.closed:
                await self.session.close()
                logger.info("HTTP session closed")

            if not self.db.dp_pool.closed:
                await self.db.close()
                logger.info("Database closed")

        except Exception as e:
            errors.append(f"HTTP or Database close error: {e}")

        if errors:
            logger.error(" | ".join(errors))

    # Методы для интеграции с жизненным циклом aiogram
    async def on_startup(self):
        """Предварительная инициализация при старте приложения"""
        try:
            async with self._lock:
                # Проверяем, не была ли уже выполнена инициализация
                if not self._initialized and not self._initialization_failed:
                    logger.info("Starting resource initialization...")
                    await self.initialize_resources()
                    self._initialized = True
                    logger.info("Resource initialization completed successfully")

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
