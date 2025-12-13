from src.config import config
from redis.asyncio.client import Redis as aioredis


class RedisService:
    def __init__(self):
        self.initialized = False

    async def get_redis_client(self):
        if not self.initialized:
            await self.connect()
        if not self.redis_client:
            raise RuntimeError("Failed to connect to Redis")
        return self.redis_client

    async def connect(self):
        if not self.initialized:
            self.redis_client = aioredis.from_url(url=config.redis.url)
            await self.redis_client.ping()
            self.initialized = True

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
            self.initialized = False


redis_service = RedisService()