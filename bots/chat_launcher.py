import logging
import socketio
from aiohttp import web
import json
import uuid
import asyncio
from datetime import datetime, timedelta
import asyncio_redis
from config import LOG_CONFIG, VERSION

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='chat_launcher')

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='aiohttp')
app = web.Application()
sio.attach(app)

# Глобальная переменная для Redis подключения
redis = None

# Хранилище для сопоставления sid с пользователями (остается в памяти)
users = {}


async def init_redis(redis_client):
    """Инициализация подключения к Redis"""
    global redis
    redis = redis_client
    logger.info("Redis подключен успешно")


async def find_partner(user_data):
    """Поиск партнера по критериям"""
    try:
        # Получаем всех пользователей из очереди поиска
        queue = await redis.lrange('partner_search_queue', 0, -1)

        for partner_json in queue:
            partner_data = json.loads(partner_json)

            # Проверяем критерии совпадения
            if user_data["criteria"].get("language") == partner_data["criteria"].get("language"):
                # Удаляем найденного партнера из очереди
                await redis.lrem('partner_search_queue', partner_json)
                return partner_data

        # Если подходящего партнера нет, добавляем в очередь
        await redis.rpush('partner_search_queue', json.dumps(user_data))
        return None

    except Exception as e:
        logger.error(f"Ошибка поиска партнера: {e}")
        return None


async def generate_link_handler(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        username = data.get("username")
        user_criteria = data.get("criteria", {})

        if not user_id or not username:
            return web.json_response({"error": "Missing user_id or username"}, status=400)

        # Сохраняем профиль пользователя в Redis
        profile_key = f"user_profile:{user_id}"
        await redis.setex(profile_key, 3600, json.dumps({
            "username": username,
            "criteria": user_criteria,
            "timestamp": datetime.now().isoformat()
        }))

        # Ищем партнера
        partner_data = await find_partner({
            "user_id": user_id,
            "username": username,
            "criteria": user_criteria
        })

        if partner_data:
            # Создаем сессию чата
            session_id = await create_chat_session(
                user1_id=user_id,
                user1_username=username,
                user2_id=partner_data["user_id"],
                user2_username=partner_data["username"]
            )

            # Генерируем ссылку для текущего пользователя
            link_token = str(uuid.uuid4())
            await redis.setex(
                f"link_token:{link_token}",
                900,
                json.dumps({
                    "user_id": user_id,
                    "username": username,
                    "session_id": session_id
                })
            )

            link = f"https://chat.lllang.site/chat?token={link_token}&v={VERSION}"

            # Генерируем ссылку для партнера
            partner_link_token = str(uuid.uuid4())
            await redis.setex(
                f"link_token:{partner_link_token}",
                900,
                json.dumps({
                    "user_id": partner_data["user_id"],
                    "username": partner_data["username"],
                    "session_id": session_id
                })
            )

            partner_link = f"https://chat.lllang.site/chat?token={partner_link_token}&v={VERSION}"

            # Сохраняем информацию о найденном партнере
            await redis.setex(
                f"partner_found:{partner_data['user_id']}",
                300,
                json.dumps({
                    "session_id": session_id,
                    "link": partner_link
                })
            )

            # Удаляем профиль партнера из Redis
            await redis.delete(f"user_profile:{partner_data['user_id']}")

            return web.json_response({
                "link": link,
                "message": "Партнер найден!",
                "status": "found",
                "session_id": session_id
            })
        else:
            return web.json_response({
                "message": "Ищем подходящего партнера...",
                "status": "searching"
            })

    except Exception as e:
        logger.error(f"Ошибка генерации ссылки: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def create_chat_session(user1_id, user1_username, user2_id, user2_username):
    """Создание сессии чата между двумя пользователями"""
    session_id = str(uuid.uuid4())

    # Сохраняем информацию о сессии в Redis
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

    await redis.setex(
        f"chat_session:{session_id}",
        900,
        json.dumps(session_data)
    )

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

    # Добавляем сообщение в Redis
    await redis.rpush(f"chat_messages:{session_id}", json.dumps(message_data))
    await redis.expire(f"chat_messages:{session_id}", 900)

    # Публикуем сообщение для real-time обновлений
    await sio.emit('new_message', message_data, room=session_id)

    return message_data["id"]


async def get_messages(session_id):
    """Получение сообщений из чата"""
    messages = await redis.lrange(f"chat_messages:{session_id}", 0, -1)
    return [json.loads(msg) for msg in messages]


async def is_session_active(session_id):
    """Проверка активности сессии чата"""
    exists = await redis.exists([f"chat_session:{session_id}"])
    return exists > 0


async def get_session_info(session_id):
    """Получение информации о сессии"""
    session_data = await redis.get(f"chat_session:{session_id}")
    if session_data:
        return json.loads(session_data)
    return None


async def update_session_info(session_id, updates):
    """Обновление информации о сессии"""
    session_info = await get_session_info(session_id)
    if session_info:
        session_info.update(updates)
        await redis.setex(
            f"chat_session:{session_id}",
            900,
            json.dumps(session_info)
        )
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

        logger.info(f"Оба пользователя согласились на обмен контактами в сессии {session_id}")
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
    await sio.emit('session_ended', {"reason": reason}, room=session_id)

    # Отключаем всех пользователей от комнаты
    session_room = sio.rooms(session_id)
    for sid in session_room:
        if sid != session_id:
            await sio.leave_room(sid, session_id)
            if sid in users:
                users[sid]["session_id"] = None

    logger.info(f"Сессия {session_id} завершена по причине: {reason}")


async def schedule_session_expiration(session_id):
    """Планировщик для автоматического завершения сессии через 15 минут"""
    await asyncio.sleep(900)

    # Проверяем, активна ли еще сессия
    if await is_session_active(session_id):
        # Предлагаем обмен контактами перед завершением
        session_info = await get_session_info(session_id)
        if session_info:
            await sio.emit('session_will_end', {
                "message": "Сессия завершается. Хотите обменяться контактами?",
                "time_left": 60
            }, room=session_id)

            # Даем дополнительную минуту на принятие решения
            await asyncio.sleep(60)

            # Завершаем сессию
            if await is_session_active(session_id):
                await end_session(session_id, "timeout")


@sio.event
async def connect(sid, environ):
    query_string = environ.get('QUERY_STRING', '')
    params = dict(param.split('=') for param in query_string.split('&') if '=' in param)

    token = params.get('token')
    if token:
        # Проверяем токен в Redis
        token_data = await redis.get(f"link_token:{token}")
        if token_data:
            user_data = json.loads(token_data)
            users[sid] = {
                "user_id": user_data["user_id"],
                "username": user_data["username"],
                "session_id": user_data.get("session_id")
            }
            logger.debug(f'Клиент {sid} подключен с userId: {user_data["user_id"]}')
            return

    # Если токен невалиден, отключаем пользователя
    await sio.disconnect(sid)
    logger.debug(f'Невалидный токен, отключение: {sid}')


@sio.event
async def disconnect(sid):
    logger.debug(f'Клиент {sid} отключен')
    if sid in users:
        if users[sid]["session_id"]:
            await sio.leave_room(sid, users[sid]["session_id"])
        del users[sid]


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

        # Генерируем ссылки для обоих пользователей
        link_token1 = str(uuid.uuid4())
        await redis.setex(
            f"link_token:{link_token1}",
            900,
            json.dumps({
                "user_id": user1_id,
                "username": user1_username,
                "session_id": session_id
            })
        )
        link1 = f"https://chat.lllang.site/chat?token={link_token1}&v={VERSION}"

        link_token2 = str(uuid.uuid4())
        await redis.setex(
            f"link_token:{link_token2}",
            900,
            json.dumps({
                "user_id": user2_id,
                "username": user2_username,
                "session_id": session_id
            })
        )
        link2 = f"https://chat.lllang.site/chat?token={link_token2}&v={VERSION}"

        # Сохраняем информацию о найденных партнерах
        await redis.setex(
            f"partner_found:{user1_id}",
            300,
            json.dumps({
                "session_id": session_id,
                "link": link1
            })
        )

        await redis.setex(
            f"partner_found:{user2_id}",
            300,
            json.dumps({
                "session_id": session_id,
                "link": link2
            })
        )

        return web.json_response({
            "session_id": session_id,
            "user1_link": link1,
            "user2_link": link2,
            "message": "Сессия создана успешно"
        })
    except Exception as e:
        logger.error(f"Ошибка при создании сессии: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def search_status_handler(request):
    try:
        user_id = request.match_info.get('user_id')

        # Проверяем, найден ли уже партнер для этого пользователя
        partner_found = await redis.get(f"partner_found:{user_id}")
        if partner_found:
            partner_data = json.loads(partner_found)
            return web.json_response({
                "status": "found",
                "session_id": partner_data["session_id"],
                "link": partner_data["link"]
            })

        # Проверяем, находится ли пользователь в процессе поиска
        user_profile = await redis.get(f"user_profile:{user_id}")
        if user_profile:
            return web.json_response({"status": "searching"})

        return web.json_response({"status": "not_found", "message": "Пользователь не в поиске"})

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса поиска: {e}")
        return web.json_response({"error": str(e)}, status=500)


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
app.router.add_get('/api/search_status/{user_id}', search_status_handler)


async def start_server(redis_client):
    global redis
    await init_redis(redis_client)

    # Запускаем сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 4000)
    await site.start()
    logger.info("Сервер запущен на localhost:4000")