# import logging
# import asyncio
# from aiogram import BaseMiddleware
# from aiogram.dispatcher.middlewares.data import MiddlewareData
# from typing import Callable, Dict, Any, Awaitable
# from aiogram.types import TelegramObject
# from aiohttp import ClientSession
#
#
# from app.dependencies import get_db, get_redis, get_redis_client
# from config import LOG_CONFIG
#
# logging.basicConfig(**LOG_CONFIG)
# logger = logging.getLogger(name="resources_middleware")
#
#
# class MyMiddlewareData(MiddlewareData):
#
#     redis: object
#     database: object
#     http_session: object
#
#
# class ResourcesMiddleware(BaseMiddleware):
#     """Middleware для управления ресурсами"""
#
#     def __init__(self):
#         self._lock = asyncio.Lock()
#         self._initialized = False
#         self._initialization_failed = False
#
#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: MyMiddlewareData,
#     ) -> Any:
#
#         data["redis"] = self.redis
#         data["database"] = self.db
#         data["http_session"] = self.session
#
#         return await handler(event, data)
#
#     async def initialize_resources(self):
#         """Инициализация ресурсов с созданием экземпляра Database"""
#         try:
#             # Инициализируем БД
#             self.db = await get_db()
#             # Создаем клиент Redis с пулом подключений
#             self.redis = await get_redis_client()
#             # Инициализация других ресурсов
#             # TODO: Вынести session в dependencies
#             self.session = ClientSession()
#             logger.debug("HTTP session initialized")
#
#         except Exception as e:
#             logger.error(f"Resource initialization failed: {e}")
#             await self._safe_close()
#             raise
#
#     async def close(self):
#         """Закрытие всех ресурсов"""
#         if self._initialized:
#             await self._safe_close()
#             self._initialized = False
#             logger.debug("All resources closed")
#
#     async def _safe_close(self):
#         """Безопасное закрытие с обработкой ошибок"""
#         try:
#             # Закрываем HTTP-сессию и пул подключений
#             # Закрываем пул подключений
#             if self.redis:
#                 await self.redis.close()
#                 logger.debug("Redis pool closed")
#             if self.session:
#                 await self.session.close()
#         except Exception as e:
#             logger.error("Error while closing resources: %s", e)
#
#     # Методы для интеграции с жизненным циклом aiogram
#     async def on_startup(self) -> None:
#         """Предварительная инициализация при старте приложения"""
#         try:
#             async with self._lock:
#                 # Проверяем, не была ли уже выполнена инициализация
#                 if not self._initialized and not self._initialization_failed:
#                     logger.debug("Starting resource initialization...")
#                     await self.initialize_resources()
#                     self._initialized = True
#                     logger.debug("Resource initialization completed successfully")
#
#         except Exception as e:
#             self._initialization_failed = True
#             logger.critical(f"Resource initialization failed: {e}", exc_info=True)
#
#             # Закрываем ресурсы, если была частичная инициализация
#             await self._safe_close()
#             raise  # Пробрасываем исключение дальше, чтобы остановить приложение
#
#         return
#
#     async def on_shutdown(self):
#         """Очистка ресурсов при остановке"""
#         await self.close()
