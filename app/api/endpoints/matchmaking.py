from fastapi import APIRouter, Depends

from app.dependencies import get_rabbitmq, get_db
from app.models import RegistrationData
from app.services.database import DatabaseService
from app.services.rabbitmq import RabbitMQService
from logging_config import opt_logger as log

router = APIRouter(prefix="/api")
logger = log.setup_logger("endpoints")


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


@router.post("/match_found")
async def save_match_id_for_users(
        match_id: str,
        rabbit: "RabbitMQService" = Depends(get_rabbitmq)
):
    """ Сохраняет в БД match_id для пары """
    await rabbit.publish_match_id(match_id)
    return {"message": "Match id успешно добавлено в БД", "status": "success"}

