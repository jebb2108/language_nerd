from datetime import datetime, timedelta
from app.dependencies import get_db, get_redis_client


async def paytime(user_id: int):
    """ Проверяет, не истекла ли подписка пользователя """
    db = await get_db()
    redis_client = await get_redis_client()
    due_to = await redis_client.get(f"user_paid:{user_id}")
    if due_to and due_to + timedelta(days=3) > datetime.now():
            return True
    elif due_to := await db.get_users_due_to(user_id) and due_to + timedelta(days=3) > datetime.now():
        await redis_client.setex(f"user_paid:{user_id}", 3600, due_to)
        return True

    return False