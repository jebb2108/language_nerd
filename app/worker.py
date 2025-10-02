import asyncio
import logging
from datetime import datetime, timedelta
from logging_config import opt_logger

from app.models import UserMatchResponse
from config import config
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from faststream.rabbit.annotations import RabbitMessage
from app.dependencies import get_match, get_notification, get_redis

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.matching import MatchingService


logger = opt_logger.setup_logger('worker')

broker = RabbitBroker(config.RABBITMQ_URL, logger=logger)

users_to_delete = {}

async def elevate_user(user_data: dict, matcher: "MatchingService") -> bool:
    """Функция для обработки состояния пользовательского инфо в очереди ожидания"""
    global users_to_delete

    logger.debug(f"Starting to elevate message ...")

    user_id = int(user_data["user_id"])
    if user_data["status"] in [
        config.SEARCH_CANCELED,
        config.SEARCH_COMPLETED
    ]:
        # Привязываем время удалений всех последующих сообщений
        # с временем первого запроса на поиск собеседника
        logger.debug(f"Copy of message %s marked as cancel/completed status", user_data["user_id"])
        if user_id in matcher.user_status:
            logger.debug(
                f"Copy message %s gets deleted from matcher.user_status", user_data["user_id"]
            )
            orig_time = matcher.user_status[user_id]["created_at"]
            users_to_delete[user_id] = orig_time

        return True

    else:
        # Обрабатываем новые сигналы на поиск партнера
        if user_id in users_to_delete:
            logger.debug("Message being prepared to be acked")
            # Проверяем, новый ли это участник?
            if users_to_delete[user_id] != user_data["created_at"]:
                del users_to_delete[user_id]
                logger.debug(f"Old msg time is deleted %s", users_to_delete[user_id])
                if user_id in matcher.user_status:
                    logger.debug(f"... so is matcher.user_status[user_id]")
                    del matcher.user_status[user_id]

    # Ситуация, когда пользователь находится в словаре
    if user_id in matcher.user_status:
        logger.debug("user_id has been in matcher's memory")
        if user_id in users_to_delete:
            saved_orig_time = datetime.fromisoformat(matcher.user_status[user_id]["created_at"])
            users_cancel_time = datetime.fromisoformat(users_to_delete[user_id])
            if saved_orig_time == users_cancel_time:
                logger.info(f"Origin msg {user_id} gets to be acked")
                return True

        # Пользователю найдена пара
        if matcher.user_status[user_id]["acked"]:
            logger.info("User %s has been processed", user_data["user_id"])
            return True

        logger.debug("Msg will go back to queue")
        return False # Статус сообщения - простое ожидание

    # Ситуация, когда пользователь НЕ находится в словаре
    else:
        matcher.user_status[user_id] = user_data
        matcher.user_status[user_id]["acked"] = False
        logger.debug("user %s has been set up in matcher's memo", user_data["user_id"])
        return False


@broker.subscriber(config.RABBITMQ_QUEUE)
async def handle_match_request(data: dict, msg: RabbitMessage):
    """Основной обработчик с встроенной задержкой"""
    global users_to_delete

    matcher = await get_match()
    notifier = await get_notification()
    redis = await get_redis()

    logger.debug(f"Received message ID: {data["user_id"]}")

    # Оцениваем сообщение по определенным параметрам
    should_ack = await elevate_user(data, matcher)
    if should_ack:
        logger.debug("Message with user ID %s acked", data["user_id"])
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

        logger.info(f"User {data["username"]} with ID {data["user_id"]} has criteria: "
                    f"{data["status"]}, "
                    f"{data["criteria"]["language"]}, "
                    f"{data["criteria"]["fluency"]}, "
                    f"{data["criteria"]["dating"]}, "
                    f"{data["gender"]}, "
                    f"{data["criteria"]["topic"]}")

        # Откладываем ack и публикуем сообщение снова через задержку
        logger.debug(f"Delaying processing for {remaining_delay:.2f} seconds for user {user_id}")
        await asyncio.sleep(remaining_delay)

        # Публикуем сообщение снова с оригинальным временем создания
        await broker.publish(
            data,
            queue=config.RABBITMQ_QUEUE,
        )
        return await msg.ack()

    # Поиск подходящей пары в Redis
    room_id, user, partner = await matcher.find_match(user_id)

    if room_id:
        # Пара найдена: уведомляем обоих пользователей
        matcher.user_status[user.user_id]["acked"] = True
        logger.debug("User %s marked as acked, expecting to be deleted", user_id)
        matcher.user_status[partner.user_id]["acked"] = True
        logger.debug(
            "User %s and user %s marked as acked, "
            "expecting to be deleted", user.user_id, partner.user_id
        )
        logger.debug("Currently only msg %s will be acked imedietly", data["user_id"])
        await notifier.notify_match(room_id, user, partner)
        await redis.remove_from_queue(user.user_id)
        await redis.remove_from_queue(partner.user_id)
        return await msg.ack()

    # Если пара не найдена, отправляем сообщение снова
    # с задержкой для повторной попытки
    retry_count = data.get("retry_count", 0)
    # Понижаем критерии поиска для участника в очереди,
    # где нет подходящей пары
    if retry_count == 5:
        data["criteria"]["dating"] = "False"
        logger.debug("User %s dating criterion changed to False", data["user_id"])
        await redis.update_user(user_id=user_id, user_data=data)

    elif retry_count == 10:
        data["criteria"]["topic"] = "general"
        logger.debug("User %s topic criterion changed to General", data["user_id"])
        await redis.update_user(user_id=user_id, user_data=data)

    elif retry_count == 15:
        indx = int(data["criteria"]["fluency"])
        if indx > 0:
            data["criteria"]["fluency"] = str(indx - 1)
            logger.debug("User %s fluency criterion decreased", data["user_id"])
            await redis.update_user(user_id=user_id, user_data=data)

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
        user_data = UserMatchResponse(
            status=config.WAITING_TIME_EXPIRED,
            user_id=data["user_id"],
            lang_code=data["lang_code"]
        )
        logger.info(f"User {user_id} has run out of time")
        # Очищаем timestamp при превышении лимита попыток
        await redis.remove_from_queue(user_id=user_id)
        await notifier.execute_time_out(user_data=user_data)

    return await msg.ack()



async def main():
    # Запуск основной программы
    logger.info('Starting worker ...')
    app = FastStream(broker, logger=logger)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
