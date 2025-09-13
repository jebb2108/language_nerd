import logging
from datetime import datetime
from uuid import uuid4

from asyncpg.pgproto.pgproto import timedelta
from redis import asyncio as aioredis

from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="matching")


class MatchingService:
    def __init__(self):
        self.redis = aioredis.from_url(config.REDIS_URL)
        self.user_status = dict()
        self.acked_users = set()

    def create_status(self, data: dict, acked=False) -> None:
        user_id = int(data["user_id"])
        if user_id not in self.user_status:
            self.user_status[user_id] = {
                "user_id": user_id,
                "status": data["status"],
                "acked": acked,
                "created_at": data['created_at']
            }
            logger.warning(
                "Users key in matcher.user_status: %s",
                self.user_status[user_id]
            )


    async def find_match(self):
        """Поиск пары пользователей"""
        queue_length = await self.redis.llen("waiting_queue")

        if queue_length >= 2:
            # Достаем двух пользователей из очереди
            # (один из них с нужным ID)
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

                if user1_id == user2_id:
                    await self.redis.lrem("waiting_queue", 1, user1_id)
                    return None, None, None

                elif self.user_status[user1_id] != self.user_status[user2_id]:
                    return None, None, None

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
