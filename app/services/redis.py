import redis.asyncio as redis
from config import config
from datetime import datetime


class RedisService:
    def __init__(self):
        self.redis_client: redis = None

    async def connect(self):
        """Установка подключения к Redis"""
        try:
            self.redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
                decode_responses=True,
            )
            # Проверяем подключение
            await self.redis_client.ping()
            print("Connected to Redis successfully")
        except Exception as e:
            print(f"Redis connection error: {e}")
            self.redis_client = None

    async def create_chat_session(self, user1_id, user2_id, room_id):
        """Создание сессии чата в Redis"""
        if not self.redis_client:
            await self.connect()

        room_data = {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "room_id": room_id,
            "created_at": str(datetime.now()),
        }

        await self.redis_client.hset(f"chat_session:{room_id}", mapping=room_data)
        # Устанавливаем TTL для сессии (например, 24 часа)
        await self.redis_client.expire(f"chat_session:{room_id}", 3600)


# Глобальный экземпляр сервиса
redis_service = RedisService()
