import redis.asyncio as redis
from config import config
from datetime import datetime


class RedisService:
    def __init__(self):
        self.redis_client: redis = None

    def get_client(self):
        return self.redis_client

    async def connect(self):
        """Установка подключения к Redis"""
        try:
            self.redis_client = redis.Redis.from_url(url=config.REDIS_URL)
            # Проверяем подключение

            print("Connected to Redis successfully")
        except Exception as e:
            print(f"Redis connection error: {e}")
            self.redis_client = None

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
