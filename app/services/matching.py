import logging
from datetime import datetime
from typing import Any, Dict, Set, Tuple, Union
from uuid import uuid4

from redis import asyncio as aioredis

from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="matching")


class MatchingService:
    def __init__(self):
        self.redis = aioredis.from_url(config.REDIS_URL)
        self.user_status: Dict[int, Dict[str, Any]] = {}
        self.acked_users: Set[int] = set()



    async def find_match(
        self, user_id: Union[int, str]
    ) -> Union[Tuple[str, int, int], Tuple[None, None, None]]:

        """Поиск пары пользователей"""
        user_id, cnt = int(user_id), 0
        queue = await self.redis.lrange("waiting_queue", 0, -1)
        user_crit = await self.redis.hgetall(f"user:{user_id}")

        user_cnt = queue.count(str(user_id).encode())
        if user_cnt > 1:
            await self.redis.lrem("waiting_queue", user_cnt-1, user_id)
            queue = await self.redis.lrange("waiting_queue", 0, -1)

        user_status = True if await self.redis.get(f"searching:{user_id}") else False

        while user_status and len(queue) >= 2 and cnt < len(queue):
            # Достаем двух пользователей из очереди
            # (один из них с нужным ID)
            cnt += 1
            partner_id = int( await self.redis.lpop("waiting_queue") )
            partner_crit = await self.redis.hgetall(f"user:{partner_id}")
            partner_status = True if await self.redis.get(f"searching:{partner_id}") else False

            # Если partner id - user id
            if user_cnt := queue.count(user_id) > 1:
                await self.redis.lrem("waiting_queue", user_cnt-1, user_id)
                break

            # Смотрим, не истекло ли TTL одного из участников
            # и не одинаковые ли ID обоих пользователей
            if not partner_status: break

            criteria_match = True
            for key in user_crit.keys():
                if key in partner_crit and user_crit[key] != partner_crit[key]:
                    criteria_match = False
                    break

            if criteria_match:

                # Создаем комнату чата
                room_id = str(uuid4())

                # Сохраняем информацию о комнате
                room_data = {
                    "user_id": user_id,
                    "partner_id": partner_id,
                    "created_at": datetime.now().isoformat(),
                }
                await self.redis.lrem("waiting_queue", 1, user_id)
                await self.redis.hset(f"room:{room_id}", mapping=room_data)
                await self.redis.expire(f"room:{room_id}", 3600)  # 1 час

                logger.info(f"Match found: {user_id} and {partner_id}, room: {room_id}")

                return room_id, user_id, partner_id

            self.redis.rpush("waiting_queue", partner_id)

        return None, None, None


matching_service = MatchingService()
