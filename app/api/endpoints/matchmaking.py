from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query

from app.dependencies import get_rabbitmq, get_db, get_ws_connection
from app.models import RegistrationData
from app.services.database import DatabaseService
from app.services.rabbitmq import RabbitMQService
from app.validators.tokens import create_token
from exc import FailToCreateToken
from logging_config import opt_logger as log

if TYPE_CHECKING:
    from app.services.connection import ConnectionService

router = APIRouter(prefix="/usr/v0")
logger = log.setup_logger("endpoints")


@router.get("/check_user")
async def check_user_handler(user_id: str, database: "DatabaseService" = Depends(get_db)):
    """Проверяет, существует ли пользователь в БД"""
    exists = await database.check_profile_exists(int(user_id))
    return {"exists": exists}

@router.post("/register")
async def register_user_handler(
        user_data: RegistrationData,
        rabbit: "RabbitMQService" = Depends(get_rabbitmq)
):
    # Сохранение в базу данных профиля пользователя
    await rabbit.publish_profile(user_data)
    return {"message": "Пользователь успешно зарегистрирован", "status": "success"}


@router.get("/user_info/{user_id}")
async def get_user_info_handler(user_id: int, database=Depends(get_db)):
    user_info = await database.get_all_user_info(user_id)

    return {
        'user_id': user_id,
        'username': user_info.get("username"),
        'gender': user_info.get('gender'),
        'criteria': {
            'language': user_info.get('language'),
            'fluency': user_info.get('fluency'),
            'topics': user_info.get('topics'),
            'dating': user_info.get('dating')
        },
        'lang_code': user_info.get('lang_code')
    }

@router.get("/create_token")
async def create_token_handler(
        user_id: int = Query(..., description="ID пользователя"),
        room_id: str = Query(..., description="Уникальный идентификатор комнаты"),
        database: "DatabaseService" = Depends(get_db)
):
    """ Обработчик создания токена """
    try:
        if not await database.check_user_exists(user_id):
            raise HTTPException(status_code=403, detail="Unauthorized attempt to create token")

        token = await create_token(user_id, room_id)
        return {"token": token}

    except FailToCreateToken:
        raise HTTPException(status_code=500, detail="Error creating token")

    except Exception as e:
        logger.error(f"Error in create_token_handler: {e}")


@router.post("/notify_session_end")
async def notify_session_end(request: dict):
    """Уведомление всех участников комнаты о завершении сессии"""
    try:
        logger.info(f"=== NOTIFY_SESSION_END CALLED ===")
        logger.info(f"Request data: {request}")

        room_id = request.get("room_id")
        reason = request.get("reason", "Session ended")

        if not room_id:
            logger.error("room_id is missing")
            raise HTTPException(status_code=400, detail="room_id is required")

        connection: "ConnectionService" = await get_ws_connection()

        # Логируем информацию о комнате
        logger.info(f"Active connections: {connection.active_connections}")
        logger.info(f"Room {room_id} connections: {connection.active_connections.get(room_id, {})}")

        # Получаем список пользователей в комнате
        users_in_room = list(connection.active_connections.get(room_id, {}).keys())
        logger.info(f"Users in room {room_id}: {users_in_room}")

        # Отправляем уведомление всем в комнате
        await connection.broadcast_to_room({
            "type": "session_ended",
            "reason": reason
        }, room_id)

        logger.info(f"Session end notification sent successfully to room {room_id}")
        return {"status": "success", "message": "Session end notification sent"}

    except Exception as e:
        logger.error(f"Error notifying session end: {e}")
        raise HTTPException(status_code=500, detail=str(e))