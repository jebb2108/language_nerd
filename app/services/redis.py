from collections import defaultdict
import redis.asyncio as redis
from typing import TYPE_CHECKING, Optional
from app.models import UserMatchRequest
from logging_config import opt_logger as log
from config import config


if TYPE_CHECKING:
    from redis.asyncio import Redis


logger = log.setup_logger('redis')


class RedisService:

    def __init__(self):
        self.redis_client: Optional["Redis"] = None
        self.q = None

    def get_client(self) -> "Redis":
        return self.redis_client

    async def connect(self):
        """Установка подключения к Redis"""
        if not self.q: self.q = defaultdict[int](list)

        try:
            self.redis_client = redis.Redis.from_url(url=config.REDIS_URL, decode_responses=True)
            logger.debug("Connected successfully")

        except Exception as e:
            logger.debug(f"Redis connection error: {e}")
            self.redis_client = None

    async def is_user_in_queue(self, user_id: id) -> bool:
        """Проверяем, находится ли пользователь в очереди"""
        queue = await self.redis_client.lrange("waiting_queue", 0, -1)
        return user_id in queue

    async def get_queue_size(self) -> int:
        """Получаем размер очереди"""
        return await self.redis_client.llen("waiting_queue")

    async def exists(self, *kwargs: str) -> bool:
        # Проверяет наличие ключей в Redis
        return bool(await self.redis_client.exists(kwargs) > 0)

    async def update_user(self, user_id: int, user_data: dict) -> None:
        # Удаляем старые данные пользователя
        await self.redis_client.delete(f"criteria:{user_id}")
        await self.redis_client.delete(f"user:{user_id}")
        # Сохраняем критерии пользователя в Redis
        await self.redis_client.hset(f"criteria:{user_id}", mapping=user_data.get("criteria"))
        # Указываем TTL для этого пользователя
        await self.redis_client.expire(f"criteria:{user_id}", config.WAIT_TIMER, nx=True)
        # Сохраняем данные пользователя в redis
        await self.redis_client.hset(
            f"user:{user_data.get("user_id")}",
            mapping={
                "username": user_data.get("username"),
                "gender": user_data.get("gender"),
                "lang_code": user_data.get("lang_code"),
            },
        )
        # Указываем TTL для этого пользователя
        await self.redis_client.expire(f"user:{user_id}", config.WAIT_TIMER)



        logger.info("User %s data has been updated on Redis side", user_id)

    async def add_to_queue(self, user_data: "UserMatchRequest") -> None:
        """Добавление пользователя в очередь поиска"""

        # Сохраняем данные пользователя в Redis
        await self.redis_client.hset(
            f"user:{user_data.user_id}",
            mapping={
                "username": user_data.username,
                "gender": user_data.gender,
                "lang_code": user_data.lang_code,
            },
        )
        # Указываем TTL для этого пользователя
        await self.redis_client.expire(f"user:{user_data.user_id}", 300, nx=True)
        # Ecтанавливаем критерии для поиска пары
        await self.redis_client.hset(f"criteria:{user_data.user_id}", mapping=user_data.criteria)
        # Устанавливаем TTL для критериев этого пользователя
        await self.redis_client.expire(f"criteria:{user_data.user_id}", 300, nx=True)
        # Добавляем в очередь поиска
        await self.redis_client.lpush("waiting_queue", user_data.user_id)
        # Устанавливаем флаг поиска
        await self.redis_client.setex(f"searching:{user_data.user_id}", config.WAIT_TIMER*2, 1)

        logger.debug(f"User {user_data.user_id} added to queue")


    async def remove_from_queue(self, user_id: int) -> None:
        """Удаление пользователя из очереди"""
        await self.redis_client.delete(f"searching:{user_id}")
        await self.redis_client.delete(f"user:{user_id}")
        await self.redis_client.delete(f"criteria:{user_id}")
        await self.redis_client.lrem("waiting_queue", 1, str(user_id))

        return logger.info(f"User {user_id} removed from queue")


# Глобальный экземпляр сервиса
redis_service = RedisService()
