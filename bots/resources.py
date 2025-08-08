# middlewares.py
import asyncio
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject
from aiohttp import ClientSession
import asyncpg

from config import db_config, logger
from database import Database  # Импортируем ваш класс DB


class ResourcesMiddleware(BaseMiddleware):
    """Middleware для управления ресурсами"""

    def __init__(self):
        super().__init__()
        self.db_config = db_config
        self.resources = {
            "db": None,  # Здесь будет экземпляр Database
            "http_session": None,
            "translation": None
        }
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

        data["resources"] = self.resources
        return await handler(event, data)

    async def initialize_resources(self):
        """Инициализация ресурсов с созданием экземпляра Database"""
        try:
            # Создаем пул подключений
            db_pool = await asyncpg.create_pool(**self.db_config)
            logger.info("Database pool created")

            # Создаем экземпляр класса Database
            self.resources["db"] = Database(db_pool)
            logger.info("Database instance initialized")

            # Инициализация других ресурсов
            self.resources["http_session"] = ClientSession()
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

        # Закрываем HTTP-сессию
        if session := self.resources.get("http_session"):
            try:
                if not session.closed:
                    await session.close()
                    logger.info("HTTP session closed")
            except Exception as e:
                errors.append(f"HTTP close error: {e}")
            finally:
                self.resources["http_session"] = None

        # Закрываем Database (вызываем его метод close)
        if db := self.resources.get("db"):
            try:
                await db.close()
                logger.info("Database closed")
            except Exception as e:
                errors.append(f"Database close error: {e}")
            finally:
                self.resources["db"] = None

        if errors:
            logger.error(" | ".join(errors))

    # Методы для интеграции с жизненным циклом aiogram
    async def on_startup(self, dispatcher):
        """Предварительная инициализация при старте"""
        try:
            async with self._lock:
                if not self._initialized and not self._initialization_failed:
                    await self.initialize_resources()
                    self._initialized = True
        except Exception as e:
            self._initialization_failed = True
            logger.critical(f"Startup initialization failed: {e}")
            raise

    async def on_shutdown(self, dispatcher):
        """Очистка ресурсов при остановке"""
        await self.close()