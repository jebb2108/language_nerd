from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.services.rabbitmq import RabbitMQService
from app.dependencies import get_rabbitmq, get_db, get_redis
from app.models import UserMatchRequest

router = APIRouter()


@router.post("/match")
async def request_match(
    request: UserMatchRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    # Проверяем пользователя в БД
    user = await db.get_user(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем, не ищет ли уже пользователь собеседника
    is_searching = await redis.get(f"searching:{request.user_id}")
    if is_searching:
        raise HTTPException(status_code=400, detail="User is already searching")

    # Сохраняем статус поиска в Redis
    await redis.setex(f"searching:{request.user_id}", 300, "true")

    # Отправляем запрос в очередь
    message = {
        "user_id": request.user_id,
        "criteria": request.criteria.dict(),
        "timestamp": datetime.now().isoformat(),
    }

    await rabbitmq.publish_message(message)

    return {"status": "search_started", "user_id": request.user_id}
