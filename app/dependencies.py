from typing import TYPE_CHECKING

from app.services.ai_modules import weekly_report_service
from app.services.rabbitmq import rabbitmq_service
from app.services.database import database_service
from app.services.matching import matching_service
from app.services.notification import notification_service
from app.services.redis import redis_service

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from app.services.database import DatabaseService
    from app.services.ai_modules import WeeklyReportScheduler, PendingReportsProcessor
    from app.services.redis import RedisService
    from app.services.rabbitmq import RabbitMQService
    from app.services.matching import MatchingService
    from app.services.notification import NotificationService


async def get_rabbitmq() -> "RabbitMQService":
    """Зависимость для получения RabbitMQ сервиса"""
    if not rabbitmq_service.connection:
        await rabbitmq_service.connect()

    return rabbitmq_service


async def get_db() -> "DatabaseService":
    """Зависимость для получения подключения к БД"""
    if not database_service.initialized:
        await database_service.connect()
    return database_service


async def get_match() -> "MatchingService":
    """Зависимость для получения Mathcing Service"""
    if not matching_service.redis:
        await matching_service.initialize()
    return matching_service


async def get_notification() -> "NotificationService":
    return notification_service


async def get_redis() -> "RedisService":
    """Зависимость для получения Redis сервиса"""
    if not redis_service.redis_client:
        await redis_service.connect()

    return redis_service


async def get_redis_client() -> "Redis":
    if not redis_service.redis_client:
        await redis_service.connect()

    return redis_service.get_client()


async def get_report_processer() -> "WeeklyReportScheduler":
    return weekly_report_service