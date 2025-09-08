import logging
from datetime import datetime
from uuid import uuid4
from redis import asyncio as aioredis

from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="matching")


class MatchingService:
    def __init__(self):
        self.redis = aioredis.from_url(config.REDIS_URL)

    async def add_to_queue(self, user_id: int, user_data: dict):
        """Добавление пользователя в очередь поиска"""
        # Сохраняем данные пользователя в Redis
        await self.redis.hset(f"user:{user_id}", mapping=user_data)
        # Указываем TTL для этого пользователя
        await self.redis.expire(f"user:{user_id}", 600, nx=True)
        # Добавляем в очередь поиска
        await self.redis.lpush("waiting_queue", user_id)
        # Устанавливаем флаг поиска
        await self.redis.setex(f"searching:{user_id}", 300, "true")

        logger.info(f"User {user_id} added to queue")

    async def remove_from_queue(self, user_id: int):
        """Удаление пользователя из очереди"""
        await self.redis.lrem("waiting_queue", 1, user_id)
        await self.redis.delete(f"searching:{user_id}")
        logger.info(f"User {user_id} removed from queue")

    async def find_match(self):
        """Поиск пары пользователей"""
        queue_length = await self.redis.llen("waiting_queue")

        if queue_length >= 2:
            # Достаем двух пользователей из очереди
            user1_id = await self.redis.rpop("waiting_queue")
            user2_id = await self.redis.rpop("waiting_queue")
            user1_crit = await self.redis.hgetall(f"user:{user1_id}")
            user2_crit = await self.redis.hgetall(f"user:{user2_id}")

            criteria_match = True
            for key in user1_crit.keys():
                if key in user2_crit and user1_crit[key] != user2_crit[key]:
                    criteria_match = False
                    break

            if criteria_match:

                user1_id = int(user1_id)
                user2_id = int(user2_id)

                # Создаем комнату чата
                room_id = str(uuid4())

                # Сохраняем информацию о комнате
                room_data = {
                    "user1_id": user1_id,
                    "user2_id": user2_id,
                    "created_at": datetime.now().isoformat(),
                }
                await self.redis.hset(f"room:{room_id}", mapping=room_data)
                await self.redis.expire(f"room:{room_id}", 3600)  # 1 час

                # Удаляем флаги поиска
                await self.redis.delete(f"searching:{user1_id}")
                await self.redis.delete(f"searching:{user2_id}")

                logger.info(f"Match found: {user1_id} and {user2_id}, room: {room_id}")

                return room_id, user1_id, user2_id

        return None, None, None


matching_service = MatchingService()
