import json
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import WebSocket, APIRouter, Query, WebSocketDisconnect, HTTPException
from starlette import status

from app.dependencies import get_ws_connection, get_redis_client
from app.models import MessageContent
from app.validators.tokens import convert_token, validate_access
from config import config
from logging_config import opt_logger as log

if TYPE_CHECKING:
    from app.services.connection import ConnectionService
    from redis.asyncio import Redis


router = APIRouter()
logger = log.setup_logger("websockets")


# WebSocket endpoint для чата
@router.websocket("/ws/chat")
async def websocket_chat(
        websocket: WebSocket,
        room_id: str = Query(..., alias="room_id"),
        token: str = Query(..., alias="token"),
):
    """Обработчик подключения клиента к чату"""

    logger.info(f"=== NEW CONNECTION ATTEMPT ===")
    logger.info(f"Room ID: {room_id}")

    connection: "ConnectionService" = await get_ws_connection()

    try:
        # Проверяем токен и получаем данные пользователя
        userdata = convert_token(token)
        username = userdata["nickname"]

        logger.info(f"User: {username}")

        if not room_id or not username:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Проверка валидности токена и прав доступа к комнате
        is_valid = await validate_access(token, room_id)
        if not is_valid:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Подключаем пользователя
        success = await connection.connect(websocket, room_id, {
            "nickname": username,
            "token": token
        })

        if not success:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        # Отправляем информацию о пользователе
        await connection.send_personal_message({
            "type": "user_info",
            "username": username
        }, websocket)

        # Отправляем историю сообщений
        history = await get_message_history(room_id)
        await connection.send_personal_message({
            "type": "message_history",
            "messages": history
        }, websocket)

        logger.info(f"User {username} successfully connected to room {room_id}")

        # Основной цикл обработки сообщений
        try:
            while True:
                # Ожидаем сообщение от клиента
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Обрабатываем отправку сообщения
                await handle_send_message(websocket, message_data)

        except WebSocketDisconnect:
            logger.info(f"User {username} disconnected from room {room_id}")

        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")

    except Exception as e:
        logger.error(f"Connection error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    finally:
        # Всегда отключаем при завершении
        await connection.disconnect(websocket)


async def handle_send_message(websocket: WebSocket, message_data: dict):
    """Обработка отправки сообщения"""

    connection: "ConnectionService" = await get_ws_connection()

    # Получаем сессию пользователя
    session = await connection.get_user_session(websocket)
    if not session:
        return

    room_id = session.get("room_id")
    username = session.get("username", "Anonymous")

    if not room_id:
        return

    # Создаем объект сообщения
    message_content = MessageContent(
        sender=username,
        text=message_data.get("text", ""),
        created_at=datetime.now(
            tz=config.TZINFO
        ).isoformat(timespec="milliseconds"),
        room_id=room_id,
    )

    # Сохранение сообщения в Redis
    await save_message(message_content)

    # Отправка сообщения всем в комнате
    await connection.broadcast_to_room({
        "type": "new_message",
        "message": message_content.model_dump()
    }, room_id)


async def save_message(message_data: "MessageContent"):
    """Сохранение сообщения в Redis"""
    redis: "Redis" = await get_redis_client()
    key = f"chat:{message_data.room_id}:messages"
    await redis.rpush(key, json.dumps(message_data.model_dump()))
    await redis.expire(key, 900)  # TTL 15 минут


async def get_message_history(room_id: str) -> list:
    """Получение истории сообщений"""
    redis: "Redis" = await get_redis_client()
    key = f"chat:{room_id}:messages"
    messages = await redis.lrange(key, 0, -1)
    return [json.loads(msg) for msg in messages]


# Эндпоинт для получения статуса комнаты
@router.get("/chat/rooms/{room_id}/status")
async def get_room_status(room_id: str):
    """Получение статуса комнаты"""
    connection: "ConnectionService" = await get_ws_connection()

    online_users = connection.get_online_users(room_id)
    return {
        "room_id": room_id,
        "user_count": len(online_users),
        "online_users": online_users
    }