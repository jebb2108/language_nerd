import asyncio

# import aiohttp
# from app.models import MatchFoundEvent
# from app.models import UserMatchResponse
# from config import config
from logging_config import opt_logger as log

logger = log.setup_logger("notification")


class NotificationService:
    def __init__(self):
        self.lock = asyncio.Lock()

    # async def execute_time_out(self, user_data: "UserMatchResponse") -> None:
    #     url = f"{config.BASE_URL}:{config.CHAT_SERVER_PORT}/api/timed_out"
    #     async with self.lock:
    #         async with aiohttp.ClientSession() as session:
    #             try:
    #                 resp = await session.post(url=url, json=user_data.model_dump())
    #                 if resp.status != 200:
    #                     error_text = await resp.text()
    #                     logger.error(
    #                         f"Failed to sent time out notification: {error_text}"
    #                     )
    #                 else:
    #                     logger.info("Time out notification sent successfully")
    #
    #                 await session.close()
    #
    #             except Exception as e:
    #                 logger.error(f"Exception during notification: {e}")
    #
    # async def notify_match(
    #     self,
    #     room_id: str,
    #     user_event: "MatchFoundEvent",
    #     partner_event: "MatchFoundEvent",
    # ) -> None:
    #     async with self.lock:
    #         url = f"{config.BASE_URL}:{config.CHAT_SERVER_PORT}/api/notify"
    #         async with aiohttp.ClientSession() as session:
    #             try:
    #                 resp = await session.post(
    #                     url=url,
    #                     json={
    #                         "room_id": room_id,
    #                         "user": user_event.model_dump(),
    #                         "partner": partner_event.model_dump(),
    #                     },
    #                 )
    #                 if resp.status != 200:
    #                     error_text = await resp.text()
    #                     logger.error(f"Failed to notify match: {error_text}")
    #                 else:
    #                     logger.info("Notification sent successfully")
    #
    #                 await session.close()
    #
    #             except Exception as e:
    #                 logger.error(f"Exception during notification: {e}")


notification_service = NotificationService()
