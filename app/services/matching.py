from datetime import datetime, timedelta
from typing import Any, Dict, Set, Tuple, Union
from uuid import uuid4

from redis.asyncio import Redis as aioredis

from app.models import ChatSessionRequest, MatchFoundEvent
from config import config
from logging_config import opt_logger as log

logger = log.setup_logger('matching')


class MatchingService:
    def __init__(self):
        self.redis = None
        self.user_status: Dict[int, Dict[str, Any]] = {}
        self.acked_users: Set[int] = set()

    async def initialize(self):
            self.redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)

    async def find_match(
        self, user_id: int
    ) -> Union[Tuple[str, MatchFoundEvent, MatchFoundEvent], Tuple[None, None, None]]:
        """Поиск пары пользователей"""
        cnt = 0
        queue = await self.redis.lrange("waiting_queue", 0, -1)
        user_crit = await self.redis.hgetall(f"criteria:{user_id}")

        user_cnt = queue.count(str(user_id))
        if user_cnt > 1:
            await self.redis.lrem("waiting_queue", user_cnt - 1, user_id)
            queue = await self.redis.lrange("waiting_queue", 0, -1)

        while len(queue) >= 2 and cnt < len(queue):
            # Достаем двух пользователей из очереди
            # (один из них с нужным ID)
            cnt += 1
            partner_id = int(await self.redis.lpop("waiting_queue"))
            partner_crit = await self.redis.hgetall(f"criteria:{partner_id}")

            criteria_match = True
            for key in user_crit.keys():
                if key in partner_crit and user_crit[key] != partner_crit[key]:
                    criteria_match = False
                    break

            if partner_id != user_id:
                if criteria_match:

                    # Создаем комнату чата
                    room_id = str(uuid4())

                    # Создаю информацию модели о матче
                    chat_session_data = ChatSessionRequest(
                        room_id=room_id,
                        user_id=user_id,
                        partner_id=partner_id,
                        matched_at=datetime.now().isoformat(),
                    )

                    user_data = await self.redis.hgetall(f"user:{user_id}")
                    partner_data = await self.redis.hgetall(f"user:{partner_id}")


                    user = MatchFoundEvent(
                        user_id=user_id,
                        username=user_data.get("username"),
                        lang_code=user_data.get("lang_code"),
                        gender=user_data.get("gender"),
                        match_criteria=user_crit,
                    )

                    partner = MatchFoundEvent(
                        user_id=partner_id,
                        username=partner_data.get("username"),
                        lang_code=partner_data.get("lang_code"),
                        gender=partner_data.get("gender"),
                        match_criteria=partner_crit,
                    )

                    # Сохраняем информацию о комнате
                    await self.redis.lrem("waiting_queue", 1, user_id)
                    await self.redis.hset(f"room:{room_id}", mapping=chat_session_data.model_dump())
                    await self.redis.expire(f"room:{room_id}", timedelta(minutes=15))

                    logger.info(
                        f"Match found: {user_id} and {partner_id}, room: {room_id}"
                    )

                    return room_id, user, partner

            await self.redis.rpush("waiting_queue", partner_id)

        return None, None, None


matching_service = MatchingService()
