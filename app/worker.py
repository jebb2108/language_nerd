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

users_to_delete = {}

async def elevate_user(user_data: dict, matcher: "MatchingService") -> bool:
    """Функция для обработки состояния пользовательского инфо в очереди ожидания"""
    global users_to_delete

    user_id = int(user_data["user_id"])

    if user_data["status"] in [
        config.SEARCH_CANCELED,
        config.SEARCH_COMPLETED
    ]:
        users_to_delete[user_id] = datetime.now(tz=config.TZINFO)
        # matcher.user_status[user_id]["status"] = user_data["status"]
        return True

    # Ситуация, когда пользователь находится в словаре
    if user_id in matcher.user_status:

        # # Пользователь завершил поиск
        if user_data["status"] != config.SEARCH_STARTED:
            if user_id in users_to_delete:

                del matcher.user_status[user_id]
                del users_to_delete[user_id]
                logger.info("deleted all info")
                return True

        # Пользователю найдена пара
        if matcher.user_status[user_id]["acked"]:
            logger.info("User has been processed")
            return True


        return False # Статус сообщения - простое ожидание

    # Ситуация, когда пользователь НЕ находится в словаре
    else:

        matcher.user_status[user_id] = user_data
        matcher.user_status[user_id]["acked"] = False
        logger.debug("user has been set up in matcher's dict")
        return False


@broker.subscriber(config.RABBITMQ_QUEUE)
async def handle_match_request(data: dict, msg: RabbitMessage):
    """Основной обработчик с встроенной задержкой"""
    logger.debug(f"Received message: {data}")

    matcher = await get_match()
    notifier = await get_notification()
    redis = await get_redis()

    # Оцениваем сообщение по определенным параметрам
    should_ack = await elevate_user(data, matcher)
    if should_ack:
        return await msg.ack()

    user_id = data.get("user_id")
    current_time = datetime.now(tz=config.TZINFO)
    message_time = datetime.fromisoformat(
        data.get("current_time", current_time.isoformat())
    )
    time_interval = current_time - message_time

    # Если прошло меньше 5 секунд, откладываем обработку
    if time_interval < timedelta(seconds=config.SLEEP_TIME):
        remaining_delay = config.SLEEP_TIME - time_interval.total_seconds()
        logger.debug(
            f"Delaying processing for {remaining_delay:.2f} seconds for user {user_id}"
        )

        logger.info(f"User {data["username"]} with ID {data["user_id"]} has the following criteria: "
                    f"Language - {data["criteria"]["language"]}, "
                    f"Fluency = {data["criteria"]["fluency"]}, "
                    f"Dating - {data["criteria"]["dating"]}, "
                    f"Topic - {data["criteria"]["topic"]} ")

        # Откладываем ack и публикуем сообщение снова через задержку
        await asyncio.sleep(remaining_delay)

        # Публикуем сообщение снова с оригинальным временем создания
        await broker.publish(
            data,
            queue=config.RABBITMQ_QUEUE,
        )
        return await msg.ack()

    # Поиск подходящей пары в Redis
    room_id, user1_id, user2_id = await matcher.find_match(user_id)

    if room_id:
        # Пара найдена: уведомляем обоих пользователей
        matcher.user_status[user1_id]["acked"] = True
        matcher.user_status[user2_id]["acked"] = True
        await notifier.notify_match(user1_id, user2_id, room_id)
        await redis.remove_from_queue(user1_id)
        await redis.remove_from_queue(user2_id)
        return await msg.ack()

    # Если пара не найдена, отправляем сообщение снова
    # с задержкой для повторной попытки
    retry_count = data.get("retry_count", 0)
    # Понижаем критерии поиска для участника в очереди,
    # где нет подходящей пары
    if retry_count == 5: data["criteria"]["dating"] = "False"
    elif retry_count == 10: data["criteria"]["topic"] = "general"
    elif retry_count == 15:
        indx = int(data["criteria"]["fluency"])
        if indx > 0: data["criteria"]["fluency"] = str(indx - 1)

    orig_time = datetime.fromisoformat(data["created_at"])
    curr_time = datetime.fromisoformat(data["current_time"])

    # Таймер на две минуты поиска
    if curr_time - orig_time  <= timedelta(seconds=config.WAIT_TIMER):

        logger.info(f"Retry {retry_count + 1} for user {user_id}")
        data["retry_count"] = retry_count + 1
        data["current_time"] = datetime.now(tz=config.TZINFO)

        await broker.publish(
            data,
            queue=config.RABBITMQ_QUEUE,
        )

    else:
        logger.info(f"User {user_id} has run out of time")
        # Очищаем timestamp при превышении лимита попыток
        await redis.remove_from_queue(user_id=user_id)

    return await msg.ack()



async def main():
    # Запуск основной программы
    app = FastStream(broker, logger=logger)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
