from fastapi import Depends
from app.services.rabbitmq import rabbitmq_service
from app.services.database import database_service
from app.services.redis import redis_service


async def get_rabbitmq():
    """Зависимость для получения RabbitMQ сервиса"""
    if not rabbitmq_service.connection:
        await rabbitmq_service.connect()
    return rabbitmq_service


async def get_db():
    """Зависимость для получения подключения к БД"""
    return await database_service.initialize()


async def get_redis():
    """Зависимость для получения Redis сервиса"""
    return redis_service
