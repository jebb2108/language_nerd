from typing import TYPE_CHECKING

from src.services.gateway import gateway_service
from src.services.redis import redis_service

if TYPE_CHECKING:
    from src.services.gateway import GatewayService
    from src.services.redis import RedisService

async def get_gateway() -> "GatewayService":
    return gateway_service

async def get_redis() -> "RedisService":
    if not redis_service.initialized:
        await redis_service.connect()
    return redis_service