from typing import TYPE_CHECKING

from app.services.rabbitmq import rabbitmq_service
from app.services.database import database_service
from app.services.matching import matching_service
from app.services.notification import notification_service
from app.services.redis import redis_service

if TYPE_CHECKING:
    from app.services.database import DatabaseService


async def get_rabbitmq():
    """Зависимость для получения RabbitMQ сервиса"""
    if not rabbitmq_service.connection:
        await rabbitmq_service.connect()

    return rabbitmq_service


async def get_db() -> "DatabaseService":
    """Зависимость для получения подключения к БД"""
    if not database_service.initialized:
        await database_service.connect()
    return database_service


async def get_match():
    """Зависимость для получения Mathcing Service"""
    return matching_service


async def get_notification():
    return notification_service


async def get_redis(call_client: bool = False):
    """Зависимость для получения Redis сервиса"""
    if not redis_service.redis_client:
        await redis_service.connect()

    if not call_client:
        return redis_service

    return redis_service.get_client()