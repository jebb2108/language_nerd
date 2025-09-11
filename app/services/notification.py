import asyncio
import logging
from datetime import datetime

import aiohttp

from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="notification")


class NotificationService:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def notify_match(self, user1_id, user2_id, room_id) -> None:
        async with self.lock:
            async with aiohttp.ClientSession() as session:
                json_data = {
                    "user1_id": int(user1_id),
                    "user2_id": int(user2_id),
                    "room_id": str(room_id),
                }

                logger.warning(f"Sending notification: {json_data}")

                try:
                    resp = await session.post(
                        url=config.NOTIFICATION_URL,
                        json=json_data,
                    )

                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Failed to notify match: {error_text}")
                    else:
                        logger.info("Notification sent successfully")

                except Exception as e:
                    logger.error(f"Exception during notification: {e}")


notification_service = NotificationService()
