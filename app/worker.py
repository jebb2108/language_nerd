import asyncio
import logging
from datetime import datetime, timedelta

from config import config, LOG_CONFIG
from faststream import FastStream
from faststream.rabbit import RabbitBroker, Channel
from faststream.rabbit.annotations import RabbitMessage
from app.dependencies import get_match, get_notification

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.matching import MatchingService

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger("worker")

broker = RabbitBroker(config.RABBITMQ_URL, logger=logger)


async def elevate_user(user_data: dict, matcher: MatchingService, msg: RabbitMessage) -> None:
    """ Функция, для обработки состояния пользовательского инфо в очереди ожидания """
    user_id, to_ack = int(user_data["user_id"]), False
    """ Ситуация, когда пользователь находится в словаре """
    if exists := int(user_data["user_id"]) in matcher.user_status:
        # Определяю, не просрочен ли таймер в информации о пользователе
        orig_time = datetime.strptime(
            matcher.user_status[user_id]['created_at'], "%Y-%m-%d %H:%M:%S"
        )
        time_period = datetime.now() - orig_time
        if expired := time_period > timedelta(minutes=3): to_ack = True
        # Глобальный параметр acked нужно только для тех сообщений,
        # когда польщователь нажал кнопку отмены в чате с ботом
        if is_acked := matcher.user_status[user_id]['acked']: to_ack = True
        if exists and is_acked and expired: del matcher.user_status[user_id]

        logger.debug("User has been processed")
        if to_ack: await msg.ack()
        return

    """ Ситуация, когда пользователь НЕ аходится в словаре """
    matcher.user_status[user_id] = user_data
    logger.debug("user has been put/updated in matcher's dict")
    return


@broker.subscriber(config.RABBITMQ_QUEUE, no_ack=True)
async def handle_match_request(data: dict, msg: RabbitMessage):

    await asyncio.sleep(2)
    logger.warning(f"Received message: {data}")

    matcher = await get_match()
    notifier = await get_notification()

    # Оцениваю сообщение по определенным параметрам
    await elevate_user(data, matcher, msg)

    # Поиск подходящей пары в Redis
    room_id, user1_id, user2_id = await matcher.find_match()

    if room_id:
        # Пара найдена: уведомляем обоих пользователей
        matcher.get_status(user1_id)['acked'] = True
        matcher.get_status(user2_id)['acked'] = True
        await notifier.notify_match(user1_id, user2_id, room_id)
        await matcher.remove_from_queue(user1_id, user2_id)

    await msg.nack()


async def main():
    app = FastStream(broker, logger=logger)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
