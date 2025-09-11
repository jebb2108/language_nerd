import json
import logging

import aio_pika
from config import config, LOG_CONFIG

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel
    from aio_pika.abc import AbstractRobustConnection

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="rabbitmq")


class RabbitMQService:
    def __init__(self):
        self.connection: Optional["AbstractRobustConnection"] = None
        self.channel: Optional["AbstractChannel"] = None
        self.default_exchange = None

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        # Объявляем обменники и очереди при подключении
        await self.declare_exchanges_and_queues()

    async def declare_exchanges_and_queues(self):
        """Объявление всех обменников и очередей"""
        # Основной обменник и очередь
        # Основной обменник и очередь

        self.default_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_EXCHANGE, type="direct"
        )
        logger.info(f"Exchange declared: {config.RABBITMQ_EXCHANGE}")

        main_queue = await self.channel.declare_queue(name=config.RABBITMQ_QUEUE)
        logger.info(f"Queue declared: {config.RABBITMQ_QUEUE}")

        await main_queue.bind(self.default_exchange, config.RABBITMQ_QUEUE)
        logger.info(
            f"Queue {config.RABBITMQ_QUEUE} bound to exchange {config.RABBITMQ_EXCHANGE} "
            f"with routing key {config.RABBITMQ_QUEUE}"
        )

    async def publish_message(self, message: dict):
        """Публикация сообщения в основную очередь"""
        json_message = json.dumps(message).encode()

        await self.default_exchange.publish(
            aio_pika.Message(
                body=json_message, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_QUEUE,
        )

    async def disconnect(self):
        """Закрытие подключения"""
        if self.connection:
            await self.connection.close()


# Глобальный экземпляр сервиса
rabbitmq_service = RabbitMQService()
