from collections import defaultdict
from typing import TYPE_CHECKING, Optional

import redis.asyncio as redis

from app.models import UserMatchRequest
from config import config
from logging_config import opt_logger as log

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


# Глобальный экземпляр сервиса
redis_service = RedisService()
