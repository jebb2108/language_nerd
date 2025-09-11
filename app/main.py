import json
import logging
import uvicorn
import jwt
import socketio
from datetime import datetime
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.endpoints import router
from app.dependencies import get_rabbitmq, get_db, get_redis
from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="fastAPI_main")

app = FastAPI(logger=logger)

origins = [
    "http://localhost:4000",  # адрес фронтенда
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация Socket.IO
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)

# Подключение к Redis
redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)


@app.get("/enter/{room_id}")
async def enter_chat(room_id: str):
    """Страница чата для конкретной комнаты"""
    return FileResponse("static/index.html")


@sio.event
async def connect(sid, environ):
    """Обработчик подключения клиента"""
    query_string = environ.get("QUERY_STRING", "")
    query_params = dict(
        param.split("=") for param in query_string.split("&") if "=" in param
    )

    room_id = query_params.get("room_id")
    token = query_params.get("token")
    userdata = convert_token(token)
    username = userdata["username"]
    logger.info("room id: %s, token: %s", room_id, token)

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

    message_data = {
        "text": message,
        "sender": username,
        "timestamp": datetime.now().isoformat(),
        "room_id": room_id,
    }

    # Сохранение сообщения в Redis
    await save_message(room_id, message_data)

    # Отправка сообщения всем в комнате
    await sio.emit("new_message", message_data, room=room_id)


async def save_message(room_id: str, message_data: dict):
    """Сохранение сообщения в Redis"""
    key = f"chat:{room_id}:messages"
    await redis.rpush(key, json.dumps(message_data))
    await redis.expire(key, 900)  # TTL 15 минут


async def get_message_history(room_id: str) -> list:
    """Получение истории сообщений"""
    key = f"chat:{room_id}:messages"
    messages = await redis.lrange(key, 0, -1)
    return [json.loads(msg) for msg in messages]


async def validate_access(token: str, room_id: str) -> bool:
    user_data = convert_token(token)
    logger.debug(f"user data {user_data}")
    if user_data["room_id"] == room_id:
        logger.debug("Аутентификация прошла успешно")
        return True  # Заглушка
    logger.debug("Некоректный token!")
    return False


def convert_token(token: str):
    """Декодирует токен по секретному ключу"""
    return jwt.decode(jwt=token, key=config.SECRET_KEY, algorithms=["HS236"])


@asynccontextmanager
async def startup(app: FastAPI):
    """Инициализация ресурсов"""
    await get_rabbitmq()
    await get_redis()
    await get_db()

    yield


app = FastAPI(lifespan=startup)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
