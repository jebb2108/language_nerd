import logging

from config import LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="notification")


class NotificationService:
    def __init__(self):
        self.cnt = 0

    async def notify_match(self, user1_id, user2_id, room_id) -> None:
        logger.info(f"Room ID: #{room_id}. Hello from {user1_id} to {user2_id}")
        self.cnt += 1


notification_service = NotificationService()
