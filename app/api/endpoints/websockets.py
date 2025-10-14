import json
from datetime import datetime
from typing import TYPE_CHECKING
from fastapi import WebSocket, APIRouter, Query, WebSocketDisconnect
from starlette import status

from app.dependencies import get_ws_connection, get_redis_client, get_redis, get_queue_service
from app.models import MessageContent
from app.services.queue import QueueService
from app.services.redis import RedisService
from app.validators.tokens import convert_token
from app.validators.validation import validate_access
from logging_config import opt_logger as log
from config import config

logger = log.setup_logger("websockets")

if TYPE_CHECKING:
    from app.services.connection import ConnectionService
    from redis.asyncio import Redis




router = APIRouter()


# WebSocket endpoint для управления очередью
@router.websocket("/ws/queue")
async def websocket_queue(
        websocket: WebSocket,
        user_id: int = Query(..., alias="user_id"),
):
    """WebSocket для управления очередью в реальном времени"""

    logger.info(f"=== NEW QUEUE CONNECTION ===")
    logger.info(f"User ID: {user_id}")

    try:
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Получаем сервисы
        redis_service: "RedisService" = await get_redis()
        connection: "ConnectionService" = await get_ws_connection()

        # Создаем QueueService
        queue_service = await get_queue_service()

        # Подключаем пользователя к комнате очереди
        success = await connection.connect(websocket, "queue", {
            "user_id": user_id,
            # "nickname": nickname
        })

        if not success:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        # Отправляем текущее состояние очереди
        queue_size = await redis_service.get_queue_size()
        user_in_queue = await redis_service.is_user_in_queue(user_id)

        await connection.send_personal_message({
            "type": "queue_initial_state",
            "queue_size": queue_size,
            "user_in_queue": user_in_queue,
            "user_id": user_id
        }, websocket)

        logger.info(f"User {user_id} connected to queue, current size: {queue_size}")

        # Основной цикл обработки сообщений
        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                if message_data.get("type") == "toggle_queue":
                    await handle_toggle_queue(
                        websocket=websocket,
                        user_id=user_id,
                        queue_service=queue_service,
                        connection=connection
                    )

        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected from queue")

    except Exception as e:
        logger.error(f"Queue connection error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        connection_service = await get_ws_connection()
        connection_service.disconnect(websocket)


async def handle_toggle_queue(
        websocket: WebSocket,
        user_id: int,
        queue_service: "QueueService",
        connection: "ConnectionService"
):
    """Обработка переключения состояния очереди с использованием QueueService"""
    try:

        # Определяем действие на основе текущего состояния
        redis: "RedisService" = await get_redis()
        user_in_queue = await redis.is_user_in_queue(user_id)
        action = "leave" if user_in_queue else "join"

        logger.info(f"User {user_id} requesting to {action} queue")

        # Используем QueueService для переключения состояния
        result = await queue_service.toggle_user_queue_status(user_id, action)

        if result["status"] == "success":
            # Обновляем всех подключенных клиентов
            queue_size = await redis.get_queue_size()

            # Рассылаем обновление всем клиентам
            await connection.broadcast_to_room({
                "type": "queue_update",
                "queue_size": queue_size,
                "timestamp": datetime.now().isoformat()
            }, "queue")

            # Отправляем персональное подтверждение
            await connection.send_personal_message({
                "type": "queue_toggle_success",
                "action": action,
                "user_in_queue": not user_in_queue,
                "queue_size": queue_size,
                "criteria": result.get("criteria", {})
            }, websocket)

            logger.info(f"User {user_id} successfully {action}ed queue. New size: {queue_size}")

        else:
            # Отправляем ошибку
            await connection.send_personal_message({
                "type": "queue_toggle_error",
                "message": result["message"],
                "action": action
            }, websocket)

            logger.error(f"Failed to {action} queue for user {user_id}: {result['message']}")

    except Exception as e:
        logger.error(f"Error handling toggle queue for user {user_id}: {e}")

        # Отправляем ошибку клиенту
        try:
            await connection.send_personal_message({
                "type": "queue_toggle_error",
                "message": "Internal server error",
                "action": "unknown"
            }, websocket)
        except:
            pass  # Если WebSocket уже закрыт



# WebSocket endpoint для создания чата
@router.websocket("/ws/chat")
async def websocket_chat(
        websocket: WebSocket,
        room_id: str = Query(..., alias="room_id"),
        token: str = Query(..., alias="token"),
        # username: str = Query(..., alias="username")
):
    """Обработчик подключения клиента к чату"""

    logger.info(f"=== NEW CONNECTION ATTEMPT ===")
    logger.info(f"Room ID: {room_id}")
    logger.info(f"Token: {token}")

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
            logger.info(f"Error in WebSocket connection: {e}")

    except Exception as e:
        logger.info(f"Connection error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    finally:
        # Всегда отключаем при завершении
        connection.disconnect(websocket)


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


# Дополнительно: эндпоинт для получения статуса комнат (опционально)
@router.get("/chat/rooms/{room_id}/status")
async def get_room_status(room_id: str):
    connection: "ConnectionService" = await get_ws_connection()
    """Получение статуса комнаты (количество участников)"""
    if room_id in connection.active_connections:
        user_count = len(connection.active_connections[room_id])
        users = []
        for ws in connection.active_connections[room_id]:
            session = connection.sessions.get(ws)
            if session:
                users.append(session["username"])

        return {
            "room_id": room_id,
            "user_count": user_count,
            "users": users
        }
    else:
        return {"room_id": room_id, "user_count": 0, "users": []}