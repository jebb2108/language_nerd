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
        self.delayed_exchange = None

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        self.channel = await self.connection.channel()

        # Объявляем обменники и очереди при подключении
        await self.declare_exchanges_and_queues()

    async def declare_exchanges_and_queues(self):
        """Объявление всех обменников и очередей"""
        # Основной обменник и очередь
        self.default_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_EXCHANGE, type="direct", durable=True
        )

        main_queue = await self.channel.declare_queue(
            name=config.RABBITMQ_QUEUE, durable=True
        )
        await main_queue.bind(self.default_exchange, config.RABBITMQ_QUEUE)

        # Отложенный обменник и очередь
        self.delayed_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_DELAYED_EXCHANGE,
            type="x-delayed-message",
            arguments={"x-delayed-type": "direct"},
            durable=True,
        )

        delayed_queue = await self.channel.declare_queue(
            name=config.RABBITMQ_DELAYED_QUEUE, durable=True
        )
        await delayed_queue.bind(self.delayed_exchange, config.RABBITMQ_DELAYED_QUEUE)

    async def publish_message(self, message: dict):
        """Публикация сообщения в основную очередь"""
        json_message = json.dumps(message).encode()

        await self.default_exchange.publish(
            aio_pika.Message(
                body=json_message, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_QUEUE,
        )

    async def publish_delayed_message(self, message: dict, delay_ms: int = 5000):
        """Публикация отложенного сообщения с задержкой"""
        json_message = json.dumps(message).encode()

        await self.delayed_exchange.publish(
            aio_pika.Message(
                body=json_message,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={"x-delay": delay_ms},
            ),
            routing_key=config.RABBITMQ_DELAYED_QUEUE,
        )

    async def disconnect(self):
        """Закрытие подключения"""
        if self.connection:
            await self.connection.close()


# Глобальный экземпляр сервиса
rabbitmq_service = RabbitMQService()
