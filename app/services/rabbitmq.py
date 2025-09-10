import json
import logging

import aio_pika
from contextlib import asynccontextmanager
from config import config, LOG_CONFIG

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel
    from aio_pika.abc import AbstractRobustConnection

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="rabbitmq")


class RabbitMQService:
    def __init__(self):
        self.connection: Optional["AbstractRobustConnection"] = (
            None  # Исправлена аннотация
        )
        self.channel: Optional["AbstractChannel"] = None
        # Хранит ссылку на обменники
        self.default_exchange = None
        self.delayed_exchange = None

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        self.channel = await self.connection.channel()

    async def declare_new_exchange(self):
        logger.info("Declaring new exchange: %s", config.RABBITMQ_EXCHANGE)
        self.default_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_EXCHANGE,
            type="direct",
        )

    async def declare_new_queue(self):
        logger.info("Declaring new queue: %s", config.RABBITMQ_QUEUE)
        queue = await self.channel.declare_queue(
            name=config.RABBITMQ_QUEUE,
        )
        await queue.bind(  # Используем await и метод bind самой очереди
            exchange=config.RABBITMQ_EXCHANGE,
            routing_key=config.RABBITMQ_QUEUE,
        )
        return queue

    async def declare_new_delayed_exchange(self):
        """Объявление отложенного обменника"""
        self.delayed_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_DELAYED_EXCHANGE,
            type="x-delayed-message",
            arguments={"x-delayed-type": "direct"},
            durable=True,
        )
        return self.delayed_exchange

    async def declare_new_delayed_queue(self):
        """Объявление и привязка очереди к отложенному обменнику"""
        # Сначала убедимся, что обменник объявлен
        if not self.delayed_exchange:
            await self.declare_new_delayed_exchange()

        # Объявляем очередь
        queue = await self.channel.declare_queue(
            name=config.RABBITMQ_DELAYED_QUEUE,
            durable=True,
        )

        # Привязываем очередь к обменнику
        await queue.bind(
            exchange=config.RABBITMQ_DELAYED_EXCHANGE,
            routing_key=config.RABBITMQ_DELAYED_QUEUE,
        )
        return queue

    async def disconnect(self):
        """Закрытие подключения"""
        if self.connection:
            await self.connection.close()

    async def publish_message(self, message: dict):
        """Публикация сообщения в обычную очередь"""
        if not self.channel:
            await self.connect()

        if not self.default_exchange:
            await self.declare_new_exchange()
            await self.declare_new_queue()

        json_message = json.dumps(message).encode()

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json_message, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_QUEUE,
        )

    async def publish_delayed_message(self, message: dict, delay_ms: int):
        """Публикация отложенного сообщения"""
        if not self.channel:
            await self.connect()

        # Убедимся, что обменник объявлен
        if not self.delayed_exchange:
            await self.declare_new_delayed_exchange()
            await self.declare_new_delayed_queue()

        json_message = json.dumps(message).encode()

        # Публикуем сообщение с указанием задержки
        await self.delayed_exchange.publish(
            aio_pika.Message(
                body=json_message,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={"x-delay": delay_ms},  # Задержка в миллисекундах
            ),
            routing_key=config.RABBITMQ_DELAYED_QUEUE,
        )

    @asynccontextmanager
    async def get_channel(self):
        """Контекстный менеджер для получения канала"""
        if not self.connection or self.connection.is_closed:
            await self.connect()

        yield self.channel


# Глобальный экземпляр сервиса
rabbitmq_service = RabbitMQService()
