import asyncio
import logging

from config import config, LOG_CONFIG
from faststream import FastStream
from faststream.rabbit import RabbitBroker, Channel
from faststream.rabbit.annotations import RabbitMessage
from app.dependencies import get_match, get_notification

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger("worker")

broker = RabbitBroker(config.RABBITMQ_URL, logger=logger)


@broker.subscriber(config.RABBITMQ_QUEUE, no_ack=True)
async def handle_match_request(data: dict, msg: RabbitMessage):

    await asyncio.sleep(2)

    logger.warning(f"Received message: {data}")

    user_id = data["user_id"]

    matcher = await get_match()
    notifier = await get_notification()

    if user_id in matcher.acked_users:
        matcher.acked_users.remove(user_id)
        logger.warning(f"User {user_id} removed from acked_users")
        await msg.ack()

    logger.warning(
        f"User {user_id} is in acked_users: {user_id in matcher.acked_users}"
    )
    # Поиск подходящей пары в Redis
    room_id, user1_id, user2_id = await matcher.find_match()

    if room_id:
        # Пара найдена: уведомляем обоих пользователей
        matcher.acked_users.update([user1_id, user2_id])
        await notifier.notify_match(user1_id, user2_id, room_id)
        await matcher.remove_from_queue(user1_id, user2_id)

    await msg.nack()


async def main():
    app = FastStream(broker, logger=logger)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
