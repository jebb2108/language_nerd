import logging
import socketio
from aiohttp import web
import json
import uuid
import asyncio
from datetime import datetime, timedelta
import asyncio_redis
from config import LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='chat_launcher')

# Создаем объект сервера
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='aiohttp')
app = web.Application()
sio.attach(app)

# Глобальная переменная для Redis подключения
client = None

# Хранилище для сопоставления sid с пользователями
users = {}
# Хранилище для активных сессий
sessions = {}


async def init_redis():
    """Инициализация подключения к Redis с использованием asyncio-redis"""
    global client
    try:
        # Создаем соединение с Redis
        client = await asyncio_redis.Pool.create(
            host='localhost',
            port=6379,
            poolsize=10
        )
        logger.info("Redis подключен успешно с использованием asyncio-redis")
    except Exception as e:
        logger.error(f"Ошибка подключения к Redis: {e}")
        raise


# Новый HTTP endpoint для генерации ссылки
async def generate_link_handler(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        username = data.get("username")

        if not user_id or not username:
            return web.json_response({"error": "Missing user_id or username"}, status=400)

        # Создаем уникальный токен для ссылки
        link_token = str(uuid.uuid4())
        logging.info(f"Generated link token: {link_token}")

        # Сохраняем в Redis на 15 минут
        await client.setex(
            f"link_token:{link_token}",
            900,
            json.dumps({"user_id": user_id, "username": username})
        )

        # Формируем ссылку (замените на ваш домен)
        link = f"https://lllang.site/chat?token={link_token}"

        return web.json_response({"link": link})

    except Exception as e:
        logger.error(f"Ошибка генерации ссылки: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def create_chat_session(user1_id, user1_username, user2_id, user2_username):
    """Создание сессии чата между двумя пользователями из Telegram"""
    session_id = str(uuid.uuid4())

    # Сохраняем информацию о сессии
    session_data = {
        "user1_id": user1_id,
        "user1_username": user1_username,
        "user2_id": user2_id,
        "user2_username": user2_username,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat(),
        "status": "active",
        "contact_exchange": {"user1_accepted": False, "user2_accepted": False}
    }

    # Сохраняем информацию о сессии в Redis
    await client.setex(
        f"chat_session:{session_id}:info",
        900,  # 15 минут в секундах
        json.dumps(session_data)
    )

    # Сохраняем в памяти для быстрого доступа
    sessions[session_id] = session_data

    # Создаем планировщик для автоматического завершения сессии
    asyncio.create_task(schedule_session_expiration(session_id))

    return session_id


async def send_message(session_id, sender_id, message_text):
    """Отправка сообщения в чат"""
    message_data = {
        "id": str(uuid.uuid4()),
        "sender": sender_id,
        "text": message_text,
        "timestamp": datetime.now().isoformat()
    }

    # Добавляем сообщение в список и устанавливаем время жизни
    await client.rpush(f"chat_session:{session_id}:messages", json.dumps(message_data))
    await client.expire(f"chat_session:{session_id}:messages", 900)

    # Публикуем сообщение для real-time обновлений
    await sio.emit('new_message', message_data, room=session_id)

    return message_data["id"]


async def get_messages(session_id):
    """Получение сообщений из чата"""
    messages = await client.lrange(f"chat_session:{session_id}:messages", 0, -1)
    return [json.loads(msg) for msg in messages]


async def is_session_active(session_id):
    """Проверка активности сессии чата"""
    if session_id in sessions:
        return sessions[session_id]["status"] == "active"

    # Проверяем существование ключа сессии в Redis
    exists = await client.exists([f"chat_session:{session_id}:info"])
    return exists > 0


async def get_session_info(session_id):
    """Получение информации о сессии"""
    if session_id in sessions:
        return sessions[session_id]

    session_data = await client.get(f"chat_session:{session_id}:info")
    if session_data:
        return json.loads(session_data)
    return None


async def update_session_info(session_id, updates):
    """Обновление информации о сессии"""
    session_info = await get_session_info(session_id)
    if session_info:
        session_info.update(updates)
        await client.setex(
            f"chat_session:{session_id}:info",
            900,  # 15 минут в секундах
            json.dumps(session_info)
        )
        sessions[session_id] = session_info
        return True
    return False


async def handle_contact_exchange(session_id, user_id, accept):
    """Обработка обмена контактами"""
    session_info = await get_session_info(session_id)
    if not session_info:
        return False

    # Определяем, какой пользователь принял решение
    if user_id == session_info["user1_id"]:
        session_info["contact_exchange"]["user1_accepted"] = accept
    elif user_id == session_info["user2_id"]:
        session_info["contact_exchange"]["user2_accepted"] = accept
    else:
        return False

    # Сохраняем обновленную информацию
    await update_session_info(session_id, session_info)

    # Проверяем, оба ли пользователя согласились на обмен
    if (session_info["contact_exchange"]["user1_accepted"] and
            session_info["contact_exchange"]["user2_accepted"]):
        # Оба согласились - отправляем контакты
        await sio.emit('contact_exchange_complete', {
            "user1_username": session_info["user1_username"],
            "user2_username": session_info["user2_username"]
        }, room=session_id)

        # Здесь должен быть код для уведомления Telegram бота о необходимости сохранить контакты
        logger.info(f"Оба пользователя согласились на обмен контактами в сессии {session_id}")

        # Завершаем сессию
        await end_session(session_id, "contact_exchange")
    else:
        # Отправляем обновление статуса
        await sio.emit('contact_exchange_update', {
            "user1_accepted": session_info["contact_exchange"]["user1_accepted"],
            "user2_accepted": session_info["contact_exchange"]["user2_accepted"]
        }, room=session_id)

    return True


async def end_session(session_id, reason="timeout"):
    """Завершение сессии"""
    await update_session_info(session_id, {"status": "ended", "end_reason": reason})

    # Отправляем событие о завершении сессии
    await sio.emit('session_ended', {"reason": reason}, room=session_id)

    # Отключаем всех пользователей от комнаты
    session_room = sio.rooms(session_id)
    for sid in session_room:
        if sid != session_id:  # Исключаем саму комнату
            await sio.leave_room(sid, session_id)
            if sid in users:
                users[sid]["session_id"] = None

    logger.info(f"Сессия {session_id} завершена по причине: {reason}")


async def schedule_session_expiration(session_id):
    """Планировщик для автоматического завершения сессии через 15 минут"""
    await asyncio.sleep(900)  # 15 минут

    # Проверяем, активна ли еще сессия
    if await is_session_active(session_id):
        # Предлагаем обмен контактами перед завершением
        session_info = await get_session_info(session_id)
        if session_info:
            await sio.emit('session_will_end', {
                "message": "Сессия завершается. Хотите обменяться контактами?",
                "time_left": 60  # 60 секунд на принятие решения
            }, room=session_id)

            # Даем дополнительную минуту на принятие решения
            await asyncio.sleep(60)

            # Завершаем сессию
            if await is_session_active(session_id):
                await end_session(session_id, "timeout")


# Обработчик подключения нового клиента
@sio.event
async def connect(sid, environ):
    query_string = environ.get('QUERY_STRING', '')
    params = dict(param.split('=') for param in query_string.split('&') if '=' in param)

    # token = params.get('token')
    token = 'jfu2ghbdcbjb'
    if token:
        # Проверяем токен в Redis
        token_data = await client.get(f"link_token:{token}")
        token_data = 'nfuwhbdcnabc927yhsjvd'
        if token_data:
            user_data = json.loads(token_data)
            users[sid] = {
                "user_id": user_data["user_id"],
                "username": user_data["username"],
                "session_id": None
            }
            logger.debug(f'Клиент {sid} подключен с userId: {user_data["user_id"]}')
            return

    # Если токен невалиден, отключаем пользователя
    await sio.disconnect(sid)
    logger.debug(f'Невалидный токен, отключение: {sid}')


# Обработчик отключения клиента
@sio.event
async def disconnect(sid):
    logger.debug(f'Клиент {sid} отключен')
    if sid in users:
        # Покидаем комнату сессии при отключении
        if users[sid]["session_id"]:
            await sio.leave_room(sid, users[sid]["session_id"])
        del users[sid]


# Обработчик присоединения к сессии
@sio.event
async def join_session(sid, data):
    session_id = data.get("session_id")
    user_id = data.get("user_id")
    username = data.get("username")

    # Проверяем существование сессии
    session_info = await get_session_info(session_id)
    if not session_info or session_info["status"] != "active":
        await sio.emit('error', {"message": "Сессия не существует или уже завершена"}, room=sid)
        return

    # Проверяем, что пользователь является участником сессии
    if user_id not in [session_info["user1_id"], session_info["user2_id"]]:
        await sio.emit('error', {"message": "Вы не являетесь участником этой сессии"}, room=sid)
        return

    # Присоединяем к комнате сессии
    await sio.enter_room(sid, session_id)
    users[sid] = {
        "user_id": user_id,
        "username": username,
        "session_id": session_id
    }

    # Отправляем историю сообщений
    messages = await get_messages(session_id)
    await sio.emit('message_history', messages, room=sid)

    # Отправляем информацию о сессии
    await sio.emit('session_info', {
        "session_id": session_id,
        "partner_username": session_info["user1_username"] if user_id == session_info["user2_id"] else session_info[
            "user2_username"],
        "expires_at": session_info["expires_at"]
    }, room=sid)

    logger.debug(f'Пользователь {username} присоединился к сессии: {session_id}')


# Обработчик отправки сообщения
@sio.event
async def send_message(sid, message_text):
    if sid not in users or not users[sid]["session_id"]:
        await sio.emit('error', {"message": "Вы не присоединены к сессии"}, room=sid)
        return

    session_id = users[sid]["session_id"]

    # Проверяем активность сессии
    if not await is_session_active(session_id):
        await sio.emit('error', {"message": "Сессия уже завершена"}, room=sid)
        return

    # Сохраняем сообщение в Redis
    await send_message(session_id, users[sid]["user_id"], message_text)
    logger.debug(f'Пользователь {users[sid]["username"]} отправил сообщение: {message_text}')


# Обработчик обмена контактами
@sio.event
async def contact_exchange(sid, decision):
    if sid not in users or not users[sid]["session_id"]:
        await sio.emit('error', {"message": "Вы не присоединены к сессии"}, room=sid)
        return

    session_id = users[sid]["session_id"]
    user_id = users[sid]["user_id"]

    # Обрабатываем решение пользователя
    success = await handle_contact_exchange(session_id, user_id, decision)

    if not success:
        await sio.emit('error', {"message": "Не удалось обработать ваше решение"}, room=sid)


# HTTP endpoint для создания сессии (вызывается Telegram ботом)
async def create_session_handler(request):
    try:
        data = await request.json()
        user1_id = data.get("user1_id")
        user1_username = data.get("user1_username")
        user2_id = data.get("user2_id")
        user2_username = data.get("user2_username")

        if not all([user1_id, user1_username, user2_id, user2_username]):
            return web.json_response({"error": "Missing required parameters"}, status=400)

        session_id = await create_chat_session(user1_id, user1_username, user2_id, user2_username)

        return web.json_response({
            "session_id": session_id,
            "message": "Сессия создана успешно"
        })
    except Exception as e:
        logger.error(f"Ошибка при создании сессии: {e}")
        return web.json_response({"error": str(e)}, status=500)


# HTTP endpoint для получения информации о сессии
async def get_session_handler(request):
    try:
        session_id = request.match_info.get('session_id')
        session_info = await get_session_info(session_id)

        if not session_info:
            return web.json_response({"error": "Сессия не найдена"}, status=404)

        return web.json_response(session_info)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о сессии: {e}")
        return web.json_response({"error": str(e)}, status=500)


# Регистрируем HTTP endpoints
app.router.add_post('/api/sessions', create_session_handler)
app.router.add_get('/api/sessions/{session_id}', get_session_handler)
app.router.add_post('/api/generate_link', generate_link_handler)


# Запуск сервера
async def start_server():
    # Инициализируем Redis
    await init_redis()
    logger.info("Redis подключен")

    # Запускаем сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 4000)
    await site.start()
    logger.info("Сервер запущен на localhost:4000")