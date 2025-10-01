import json
import logging
import redis.asyncio as redis
from typing import TYPE_CHECKING, Optional

from app.models import UserMatchRequest
from config import config
from logging_config import setup_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from app.models import SentMessage

logger = setup_logger('redis')


class RedisService:

    def __init__(self):
        self.redis_client: Optional["Redis"] = None

    def get_client(self) -> "Redis":
        return self.redis_client

    async def connect(self):
        """Установка подключения к Redis"""
        try:
            self.redis_client = redis.Redis.from_url(url=config.REDIS_URL)
            logger.debug("Connected successfully")

        except Exception as e:
            logger.debug(f"Redis connection error: {e}")
            self.redis_client = None

    async def save_sent_message(
        self, chat_id: int, message_info: "SentMessage", ttl: int
    ):
        # Сохряняет сообщения, которые нужно удалить через некоторое время
        key = f"search_message:{chat_id}"
        await self.redis_client.hset(key, mapping=message_info.model_dump())
        # Устанавливает время жизни для сообщения
        await self.redis_client.expire(key, ttl)
        # Добавляет в очередь сообщения
        await self.redis_client.rpush("sent_messages", message_info.message_id)

        logger.debug(f"Message {message_info.message_id} has been saved on Redis side")

    async def get_search_message_id(self, chat_id: int):
        # Достает определенное сообщение
        key = f"search_message:{chat_id}"
        res = await self.redis_client.hget(key, "message_id")
        logger.debug(f"Search message id for user {chat_id}: {res}")
        return res

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
        logger.info(f"Adding user {user_data.user_id} to queue")
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
        await self.redis_client.setex(f"searching:{user_data.user_id}", 300, "true")

        logger.info(f"User {user_data.user_id} added to queue")


    async def remove_from_queue(self, user_id: int) -> None:
        """Удаление пользователя из очереди"""
        await self.redis_client.delete(f"searching:{user_id}")
        await self.redis_client.delete(f"user:{user_id}")
        await self.redis_client.delete(f"criteria{user_id}")
        await self.redis_client.lrem("waiting_queue", 1, str(user_id))

        return logger.info(f"User {user_id} removed from queue")


# Глобальный экземпляр сервиса
redis_service = RedisService()
