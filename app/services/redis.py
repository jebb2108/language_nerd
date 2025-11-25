import json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Optional

import redis.asyncio as redis
from redis.asyncio.utils import pipeline

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

    async def get_searched_words(self, word: str) -> dict:
        async with self.transaction() as pipe:
            words_dict = await pipe.hget(f"searched_word:{word}")
        return { k: json.loads(v) for k ,v in words_dict } if words_dict else None

    async def save_search_result(self, word, all_users_words, interval: timedelta):
        async with self.transaction() as pipe:
            key = f"searched_word:{word}"
            for nickname, word_data in all_users_words.items():
                await pipe.hset(key, nickname, json.dumps(word_data))
            await pipe.expire(key, interval)

    @asynccontextmanager
    async def transaction(self):
        try:
            async with self.redis_client.pipeline() as pipe:
                yield pipe
                await pipe.execute()

        except Exception as e:
            logger.warning(f"Error handling redis transaction: {e}")
            raise

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
