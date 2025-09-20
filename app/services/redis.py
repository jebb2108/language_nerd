import logging
from typing import Union
import redis.asyncio as redis

from config import config, LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='redis')



class RedisService:

    def __init__(self):
        self.redis_client: redis = None

    def get_client(self):
        return self.redis_client

    async def connect(self):
        """Установка подключения к Redis"""
        try:
            self.redis_client = redis.Redis.from_url(url=config.REDIS_URL)
            logger.debug('Connected successfully')

        except Exception as e:
            logger.debug(f"Redis connection error: {e}")
            self.redis_client = None


    async def add_to_queue(self, user_id: int, user_data: dict) -> None:
        """Добавление пользователя в очередь поиска"""
        logger.info(f"Adding user {user_id} to queue")
        # Сохраняем данные пользователя в Redis
        await self.redis_client.hset(f"user:{user_id}", mapping=user_data)
        # Указываем TTL для этого пользователя
        await self.redis_client.expire(f"user:{user_id}", 300, nx=True)
        # Добавляем в очередь поиска
        await self.redis_client.lpush("waiting_queue", user_id)
        # Устанавливаем флаг поиска
        await self.redis_client.setex(f"searching:{user_id}", 300, "true")

        logger.info(f"User {user_id} added to queue")

    async def remove_from_queue(self, user_id: int, partner_id: Union[int, None] = None) -> None:
        """Удаление пользователя из очереди"""
        await self.redis_client.lrem("waiting_queue", 1, user_id)
        await self.redis_client.delete(f"searching:{user_id}")
        # Если только одного человека удаляем
        if not partner_id: return logger.info(f"Users {user_id} removed from queue")
        # Удаляем второго пользователя из очереди
        await self.redis_client.lrem("waiting_queue", 1, partner_id)
        await self.redis_client.delete(f"searching:{partner_id}")
        return logger.info(f"Users {user_id} and {partner_id} removed from queue")

    async def create_chat_session(self, room_id, user1_id, user2_id):
        """Создание сессии чата в Redis"""
        if not self.redis_client:
            await self.connect()

        room_data = {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "room_id": room_id,
        }

        await self.redis_client.hset(f"chat_session:{room_id}", mapping=room_data)
        # Устанавливаем TTL для сессии (например, 30 минут)
        await self.redis_client.expire(f"chat_session:{room_id}", 1800)


# Глобальный экземпляр сервиса
redis_service = RedisService()
