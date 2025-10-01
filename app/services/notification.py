import asyncio
import logging
import aiohttp

from typing import TYPE_CHECKING
from config import LOG_CONFIG, config

if TYPE_CHECKING:
    from app.models import UserMatchRequest

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="notification")


class NotificationService:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def execute_time_out(self, user_data: "UserMatchRequest") -> None:
        url = f"{config.BASE_URL}:{config.CHAT_SERVER_PORT}/api/timed_out"
        async with self.lock:
                async with aiohttp.ClientSession() as session:
                    try:
                        resp = await session.post(
                            url=url,
                            json=user_data.model_dump()
                        )
                        if resp.status != 200:
                            error_text = await resp.text()
                            logger.error(f"Failed to sent time out notification: {error_text}")
                        else:
                            logger.info("Time out notification sent successfully")

                        await session.close()

                    except Exception as e:
                        logger.error(f"Exception during notification: {e}")


    async def notify_match(self, user1_id, user2_id, room_id) -> None:
        async with self.lock:
            async with aiohttp.ClientSession() as session:
                json_data = {
                    "user_id": int(user1_id),
                    "partner_id": int(user2_id),
                    "room_id": str(room_id),
                }

                logger.warning(f"Sending notification: {json_data}")
                url = f"{config.BASE_URL}:{config.CHAT_SERVER_PORT}/api/notify"

                try:
                    resp = await session.post(
                        url=url,
                        json=json_data,
                    )

                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Failed to notify match: {error_text}")
                    else:
                        logger.info("Notification sent successfully")

                    await session.close()

                except Exception as e:
                    logger.error(f"Exception during notification: {e}")



notification_service = NotificationService()
