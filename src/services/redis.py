from src.config import config
from redis.asyncio.client import Redis as aioredis


class RedisService:
    def __init__(self):
        self.initialized = False

    def get_redis_client(self):
        if self.initialized:
            return self.redis_client

    def connect(self):
        if not self.initialized:
            self.redis_client = aioredis.from_url(url=config.redis.url)

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.aclose()


redis_service = RedisService()