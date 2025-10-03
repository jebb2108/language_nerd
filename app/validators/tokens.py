import jwt
from config import config
from datetime import datetime, timedelta
from app.dependencies import get_db


async def create_token(user_id, room_id, exp: timedelta = timedelta(minutes=15)):
    """Функция для выдачи уникального токена пользоватеою, содержащую его данные"""

    db = await get_db()
    users_profile = await db.get_users_profile(user_id)
    username = users_profile["username"]
    time_obj = datetime.now() + exp

    payload = {
        "user_id": user_id,
        "username": username,
        "room_id": room_id,
        "expires_at": time_obj.isoformat(),
    }

    token = jwt.encode(payload=payload, key=config.SECRET_KEY, algorithm="HS256")
    return token


def convert_token(token: str):
    """Декодирует токен по секретному ключу"""
    return jwt.decode(jwt=token, key=config.SECRET_KEY, algorithms=["HS256"])
