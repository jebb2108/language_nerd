from datetime import datetime, timedelta

from app.dependencies import get_db


async def paytime(user_id: int):
    db = await get_db()
    created_at = await db.get_users_created_at(user_id)
    created_at_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    print(created_at_obj)
    if created_at_obj + timedelta(days=3) > datetime.now() - timedelta(days=4):
        return True
    return False