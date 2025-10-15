import asyncio
from typing import TYPE_CHECKING
from aiogram.enums import ParseMode
from fastapi import APIRouter, Depends, HTTPException

from app.models import UserMatchResponse
from app.dependencies import get_rabbitmq, get_db, get_redis, get_partner_bot, get_redis_client, get_queue_service
# from app.bots.main_bot.keyboards.inline_keyboards import create_start_chat_button
from app.bots.partner_bot.translations import MESSAGES
from app.services.database import DatabaseService
from app.services.redis import RedisService
# from app.validators.tokens import create_token
from config import config
from logging_config import opt_logger as log
from app.models import UserMatchRequest, RegistrationData, WebMatchToggleRequest
from app.services.rabbitmq import RabbitMQService
from app.services.queue import QueueService

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = log.setup_logger("endpoints", config.LOG_LEVEL)


router = APIRouter(prefix="/api")


@router.get("/check_user")
async def check_user(user_id: str, database: "DatabaseService" = Depends(get_db)):
    """Проверяет, существует ли пользователь в БД"""
    exists = await database.check_profile_exists(int(user_id))
    return {"exists": exists}

@router.post("/register")
async def register_user(
        user_data: RegistrationData,
        rabbit: "RabbitMQService" = Depends(get_rabbitmq)
):
    # Сохранение в базу данных профиля пользователя
    await rabbit.publish_profile(user_data)
    return {"message": "Пользователь успешно зарегистрирован", "status": "success"}


@router.get("/queue/status")
async def get_queue_status(
        redis_client: "Redis" = Depends(get_redis_client)
):
    """Получение текущего статуса очереди"""
    queue_size = await redis_client.llen("waiting_queue")
    return {
        "queue_size": queue_size,
        "status": "active" if queue_size > 0 else "empty"
    }


@router.get("/queue/user/{user_id}/status")
async def get_user_queue_status(
        user_id: str,
        redis_client: "Redis" = Depends(get_redis_client)
):
    """Получение статуса пользователя в очереди"""
    queue = await redis_client.lrange("waiting_queue", 0, -1)
    in_queue = user_id in queue

    return {
        "user_id": user_id,
        "in_queue": in_queue,
        "position": queue.index(user_id) + 1 if in_queue else None
    }


@router.post("/match/toggle")
async def toggle_match_status(
        request: WebMatchToggleRequest,
        queue_service: QueueService = Depends(get_queue_service)
):
    """Профессиональный endpoint для управления очередью"""
    result = await queue_service.toggle_user_queue_status(
        user_id=request.user_id,
        action=request.action
    )

    if result["status"] == "error" and result["message"] == "User not found":
        raise HTTPException(status_code=400, detail=result["message"])
    if result["status"] == "error" and result["message"] == "User not active":
        raise HTTPException(status_code=403, detail=result["message"])

    return result


@router.post("/match")
async def request_match(
        request: "UserMatchRequest",
        database: "DatabaseService" = Depends(get_db),
        rabbitmq: "RabbitMQService" = Depends(get_rabbitmq),
):
    """Основной обработчик поиска собеседника"""
    # Проверяем пользователя в базе
    user_exists = await database.check_user_exists(user_id=request.user_id)
    if not user_exists:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")

    logger.info(
        f"Match request - User: {request.user_id}, "
        f"Criteria: {request.criteria}, "
        f"Status: {request.status}"
    )

    redis = await get_redis()

    # Сохраняем статус поиска в Redis
    if request.status == config.SEARCH_STARTED:
        logger.info(f"Adding user {request.user_id} to queue")
        await redis.add_to_queue(request)
    elif request.status == config.SEARCH_CANCELED:
        logger.info(f"Removing user {request.user_id} from queue")
        await redis.remove_from_queue(request.user_id)

    # Отправляем запрос в очередь RabbitMQ
    await rabbitmq.publish_request(request.model_dump())
    return {"status": "success", "action": request.status}