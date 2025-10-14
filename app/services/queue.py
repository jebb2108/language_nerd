from typing import Dict, Any, TYPE_CHECKING

from app.models import UserMatchRequest
from logging_config import opt_logger as log
from config import config

if TYPE_CHECKING:
    from app.services.redis import RedisService

logger = log.setup_logger("toggle_service")

class QueueService:
    def __init__(self):
        self.database = None
        self.rabbitmq = None
        self.initialized = False

    async def connect(self):
        if not self.initialized:
            from app.dependencies import get_db, get_rabbitmq
            self.database = await get_db()
            self.rabbitmq = await get_rabbitmq()
            self.initialized = True

    async def toggle_user_queue_status(self, user_id: int, action: str) -> Dict[str, Any]:
        """Переключает статус пользователя в очереди"""
        try:
            # Получаем данные пользователя
            user_profile = await self.database.get_all_user_info(user_id)
            if not user_profile:
                return {"status": "error", "message": "User not found"}
            if not user_profile.get("is_active"):
                return {"status": "error", "message": "User is not active"}

            # Определяем статус
            status = config.SEARCH_STARTED if action == "join" else config.SEARCH_CANCELED

            criteria = {
                "language": user_profile.get("language"),
                "topic": user_profile.get("topic"),
                "fluency": user_profile.get("fluency"),
                "dating": str(user_profile.get("dating"))
            }

            # Создаем запрос для матчинга
            match_request = UserMatchRequest(
                user_id=user_id,
                username=user_profile["username"],
                gender=user_profile["gender"],
                lang_code=user_profile["lang_code"],
                criteria=criteria,
                status=status,
                source="web"
            )


            # Отправляем в RabbitMQ
            await self.rabbitmq.publish_request(match_request.model_dump())

            from app.dependencies import get_redis
            redis: "RedisService" = await get_redis()
            if action == "join":
                await redis.add_to_queue(match_request)
            elif action == "leave":
                await redis.remove_from_queue(match_request.user_id)

            logger.info(f"User {user_id} {action} queue successfully")

            return {
                "status": "success",
                "action": action,
                "user_id": user_id,
                "criteria": criteria
            }

        except Exception as e:
            logger.error(f"Error toggling queue for user {user_id}: {e}")
            return {"status": "error", "message": str(e)}


queue_service = QueueService()