import json
import aio_pika
from contextlib import asynccontextmanager
from config import config

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel, AbstractRobustConnection


class RabbitMQService:
    def __init__(self):
        self.connection: Optional["AbstractRobustConnection", None] = None
        self.channel: Optional["AbstractChannel", None] = None

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        # await self.channel.declare_queue(config.RABBITMQ_QUEUE, durable=False)

    async def disconnect(self):
        """Закрытие подключения"""
        if self.connection:
            await self.connection.close()

    async def publish_message(self, message: dict):
        """Публикация сообщения в очередь"""
        if not self.channel:
            await self.connect()

        json_message = json.dumps(message).encode()

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json_message, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_QUEUE,
        )

    @asynccontextmanager
    async def get_channel(self):
        """Контекстный менеджер для получения канала"""
        if not self.connection or self.connection.is_closed:
            await self.connect()

        yield self.channel


# Глобальный экземпляр сервиса
rabbitmq_service = RabbitMQService()
