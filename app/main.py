import asyncio
import logging

from app.dependencies import get_match, get_notification, get_db, get_redis
from config import config, LOG_CONFIG

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="FastStream")

# Создаем брокер и приложение
broker = RabbitBroker(config.RABBITMQ_URL)


# Определяем обработчик сообщений
@broker.subscriber(config.RABBITMQ_QUEUE)
async def handle_user_match(message: dict):
    """
    Обрабатывает сообщения из очереди user_matching_queue
    """
    logger.info("data: %r", repr(message))

    user_id = message.get("user_id")
    user_data = dict(message["criteria"])

    logger.info(
        f"Received match request from user {user_id} with criteria: {user_data}"
    )

    matcher = await get_match()
    notifier = await get_notification()
    # redis = await get_redis()
    room_id, user1_id, user2_id = await matcher.find_match()

    if room_id:
        # Уведомляем пользователей
        await matcher.remove_from_queue(user_id)
        await notifier.notify_match(user1_id, user2_id, room_id)
        # await redis.create_chat_session(user1_id, user2_id, room_id)
        await asyncio.sleep(5)
        return f"Match created: {room_id}"

    else:

        # Совпадение не найдено
        logger.debug(f"No match for {user_id}. Returning to queue.")

        # Сохраните пользователя в Redis
        await matcher.add_to_queue(user_id, user_data)  # TTL 1 час

        # Верните сообщение в очередь через delay (например, через 10 секунд)
        # Публикация сообщения в отложенный обменник с задержкой
        await broker.publish(
            message,
            exchange="",
            routing_key=config.RABBITMQ_QUEUE,
            headers={"x-delay": 10000},  # Задержка 10 секунд
        )

        # Или используйте DLX для отложенной повторной публикации
        # Подтвердите сообщение, чтобы оно не вернулось сразу
        return {"status": "requeued", "user_id": user_id}


app = FastStream(broker)
