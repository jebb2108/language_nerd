import asyncio
import logging
from datetime import datetime, timedelta

from config import config, LOG_CONFIG
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from faststream.rabbit.annotations import RabbitMessage
from app.dependencies import get_match, get_notification, get_redis

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.matching import MatchingService

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger("worker")

broker = RabbitBroker(config.RABBITMQ_URL, logger=logger)


async def elevate_user(user_data: dict, matcher: "MatchingService") -> bool:
    """ Функция, для обработки состояния пользовательского инфо в очереди ожидания """
    user_id, to_ack = int(user_data["user_id"]), False

    if user_data['status'] in [
        config.SEARCH_CANCELED, 
        config.SEARCH_COMPLETED
        ]:

        matcher.set_status(data=user_data, acked=True)
        return True

    """ Ситуация, когда пользователь находится в словаре """
    if int(user_data["user_id"]) in matcher.user_status:
        # Определяю, не просрочен ли таймер в информации о пользователе
        orig_time = datetime.fromisoformat(
            matcher.user_status[user_id]['created_at']
        )
        # Проверка на просроченность
        time_period = datetime.now(tz=config.TZINFO) - orig_time
        if time_period > timedelta(minutes=3): 
            del matcher.user_status[user_id]
            to_ack = True
        # Глобальный параметр acked нужно только для тех сообщений,
        # когда пользователь нажал кнопку отмены в чате с ботом или нашел партнера
        elif matcher.user_status[user_id]['acked']: to_ack = True
    
        logger.debug("User has been processed")
        if to_ack: return True

    """ Ситуация, когда пользователь НЕ аходится в словаре """
    matcher.set_status(data=user_data)
    logger.debug("user has been set up in matcher's dict")
    return False


@broker.subscriber(config.RABBITMQ_QUEUE)
async def handle_match_request(data: dict, msg: RabbitMessage):

    current_time = datetime.now(tz=config.TZINFO)
    message_time = datetime.fromisoformat(data.get("current_time", datetime.now(tz=config.TZINFO).isoformat()))
    if current_time - message_time < timedelta(seconds=1):
        return await msg.nack()
    
    updated_data = data.copy()
    updated_data["current_time"] = current_time.isoformat()
        
    logger.warning(f"Received message: {data}")
    logger.warning(f"Message after processing: {updated_data}")

    matcher = await get_match()
    notifier = await get_notification()
    redis = await get_redis()
    
    # Оцениваю сообщение по определенным параметрам
    should_ack = await elevate_user(data, matcher)
    if should_ack: return await msg.ack()

    # Поиск подходящей пары в Redis
    room_id, user1_id, user2_id = await matcher.find_match(updated_data["user_id"])

    if room_id:
        # Пара найдена: уведомляем обоих пользователей
        matcher.set_status(data=data, acked=True)
        matcher.set_status(data=data, acked=True)
        await notifier.notify_match(user1_id, user2_id, room_id)
        await redis.remove_from_queue(user1_id, user2_id)

    await msg.nack()
    return updated_data


async def main():
    app = FastStream(broker, logger=logger)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
