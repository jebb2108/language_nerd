from datetime import datetime

import jwt
from asyncpg.pgproto.pgproto import timedelta

from config import config
from app.dependencies import get_db


async def create_token(user_id, room_id, exp: timedelta = timedelta(minutes=15)):
    """Функция для выдачи уникального токена пользоватеою, содержащую его данные"""
    db = await get_db()
    users_profile = await db.get_users_profile(user_id)
    nickname = users_profile["prefered_name"]

    time_obj = datetime.now() + exp

    payload = {
        "user_id": user_id,
        "username": nickname,
        "room_id": room_id,
        "expires_at": time_obj.isoformat(),
    }

    token = jwt.encode(payload=payload, key=config.SECRET_KEY, algorithm=["HS236"])
    return token
