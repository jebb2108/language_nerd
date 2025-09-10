import logging

from config import config, LOG_CONFIG
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from app.dependencies import get_rabbitmq, get_match, get_notification

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="faststream")

# Создаем брокер и приложение FastStream
broker = RabbitBroker(config.RABBITMQ_URL)


# Определяем обработчик сообщений для основной очереди
@broker.subscriber(config.RABBITMQ_QUEUE)
async def handle_user_match(message: dict):
    """
    Обрабатывает сообщения из основной очереди пользователей
    """
    logger.info("Received message from main queue: %r", message)

    user_id = message.get("user_id")
    user_data = message.get("criteria", {})

    # Здесь ваша логика проверки критериев пользователя
    matcher = await get_match()
    rabbit = await get_rabbitmq()

    room_id, user1_id, user2_id = await matcher.find_match(user_id, user_data)

    if room_id:
        # Найдено совпадение - обрабатываем
        notifier = await get_notification()
        await matcher.remove_from_queue(user_id)
        await notifier.notify_match(user1_id, user2_id, room_id)
        logger.info(f"Match created: {room_id}")
        return f"Match created: {room_id}"

    else:
        # Совпадение не найдено - отправляем в отложенную очередь
        delay_ms = message.get("delay_ms", 10000)  # Задержка по умолчанию 10 секунд

        # Используем наш сервис для публикации в отложенную очередь
        await rabbit.publish_delayed_message(message, delay_ms)
        logger.debug(f"No match for {user_id}. Sent to delayed queue for {delay_ms}ms.")

        return {"status": "requeued", "user_id": user_id, "delay_ms": delay_ms}


# Определяем обработчик для отложенной очереди
@broker.subscriber(config.RABBITMQ_DELAYED_QUEUE)
async def handle_delayed_user(message: dict, headers: dict = None):
    """
    Обрабатывает сообщения из отложенной очереди
    Просто возвращает пользователя в основную очередь
    """
    rabbit = await get_rabbitmq()
    logger.info("Received message from delayed queue: %r", message)
    # Извлекаем задержку из заголовков
    delay_ms = headers.get("x-delay", 10000) if headers else 10000
    logger.debug(f"Message was delayed for {delay_ms}ms")

    # Возвращаем пользователя в основную очередь
    await rabbit.publish_message(message)
    logger.debug(f"Returned user {message.get('user_id')} to main queue")


app = FastStream(broker)
