import json

import uvicorn
import socketio
from datetime import datetime
from fastapi import FastAPI
from pamqp.decode import timestamp
from redis.asyncio import Redis

from app.dependencies import get_redis_client, get_rabbitmq
from app.models import MessageContent
from app.services.rabbitmq import RabbitMQService
from app.validators.tokens import convert_token
from app.validators.validation import validate_access
from config import config

from app.api.endpoints.matchmaking import router as match_router

from logging_config import opt_logger as log

logger = log.setup_logger("chat server")

# Создаем единственный экземпляр FastAPI
app = FastAPI()

# Подключаем роутеры
app.include_router(match_router)

# Инициализация Socket.IO
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)

# Подключение к Redi


@sio.event
async def connect(sid, environ):
    """Обработчик подключения клиента"""
    print(f"=== NEW CONNECTION ATTEMPT ===")
    print(f"SID: {sid}")
    print(f"Environ: {environ}")

    query_string = environ.get("QUERY_STRING", "")
    print(f"Query string: {query_string}")

    query_params = dict(
        param.split("=") for param in query_string.split("&") if "=" in param
    )

    room_id = query_params.get("room_id")
    token = query_params.get("token")
    userdata = convert_token(token)
    username = userdata["nickname"]
    print("room id: %s, token: %s", room_id, token)

    if not room_id or not token:
        raise ConnectionRefusedError("Authentication failed")

    # Проверка валидности токена и прав доступа к комнате
    is_valid = await validate_access(token, room_id)
    if not is_valid:
        raise ConnectionRefusedError("Access denied")

    # Сохраняем сессию
    await sio.save_session(
        sid,
        {
            "room_id": room_id,
            "token": token,
            "username": username,
        },
    )

    # Входим в комнату
    await sio.enter_room(sid, room_id)

    # Отправляем информацию о пользователе на фронтенд
    await sio.emit("user_info", {"username": username}, room=sid)

    # Отправка истории сообщений
    history = await get_message_history(room_id)
    await sio.emit("message_history", history, room=sid)


@sio.event
async def disconnect(sid):
    """Обработчик отключения клиента"""
    session = await sio.get_session(sid)
    room_id = session.get("room_id")
    if room_id:
        await sio.leave_room(sid, room_id)


@sio.event
async def send_message(sid, message):
    """Обработка отправки сообщения"""
    session = await sio.get_session(sid)
    room_id = session.get("room_id")
    username = session.get("username", "Anonymous")

    if not room_id:
        return

    message_data = MessageContent(
        sender=username,
        text=message,
        created_at=datetime.now(
            tz=config.TZINFO
        ).isoformat(timespec="milliseconds"),
        room_id=room_id,
    )

    # Сохранение сообщения в Redis
    await save_message(message_data)

    # Отправка сообщения всем в комнате
    await sio.emit("new_message", message_data.model_dump(), room=room_id)


async def save_message(message_data: "MessageContent"):
    """Сохранение сообщения в Redis"""
    # rabbit: "RabbitMQService" = await get_rabbitmq()
    redis: "Redis" = await get_redis_client()
    key = f"chat:{message_data.room_id}:messages"
    await redis.rpush(key, json.dumps(message_data.model_dump()))
    await redis.expire(key, 900)  # TTL 15 минут

    # await rabbit.publish_message(message_data)


async def get_message_history(room_id: str) -> list:
    """Получение истории сообщений"""
    redis: "Redis" = await get_redis_client()
    key = f"chat:{room_id}:messages"
    messages = await redis.lrange(key, 0, -1)
    return [json.loads(msg) for msg in messages]


if __name__ == "__main__":
    uvicorn.run(
        "app.chat_server:socket_app",
        host="localhost",
        port=config.CHAT_SERVER_PORT,
        reload=True,
    )
