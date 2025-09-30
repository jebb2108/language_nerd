from datetime import datetime, timedelta

from app.dependencies import get_db


async def paytime(user_id: int):
    db = await get_db()
    due_to = await db.get_users_due_to(user_id)
    if due_to + timedelta(days=3) > datetime.now() - timedelta(days=4):
        return True
    return False