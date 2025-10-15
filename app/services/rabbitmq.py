import json
from typing import TYPE_CHECKING, Optional

import aio_pika

from app.models import (
    Location, MessageContent,
    NewPayment, NewUser,
    RegistrationData, UserMatchRequest
)
from config import config
from logging_config import opt_logger as log

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel
    from aio_pika.abc import AbstractRobustConnection
    from app.models.bot_models import NewUser


logger = log.setup_logger('rabbitmq')


class RabbitMQService:
    def __init__(self):
        self.connection: Optional["AbstractRobustConnection"] = None
        self.channel: Optional["AbstractChannel"] = None
        self.default_exchange = None
        self.new_users_exchange = None
        self.messages_exchange = None

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        # Объявляем обменники и очереди при подключении
        await self.declare_exchanges_and_queues()

    async def declare_exchanges_and_queues(self):
        """Объявление всех обменников и очередей"""
        """
        Объясвляем обменник и очередь для обрабтки пользовательской информации
        """
        self.new_users_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_NEW_USERS_EXCHANGE, type="direct"
        )
        new_users_queue = await self.channel.declare_queue(name=config.RABBITMQ_NEW_USERS_QUEUE)
        await new_users_queue.bind(self.new_users_exchange, config.RABBITMQ_NEW_USERS_QUEUE)

        """
        Объясвляем обменник и очередь для обрабтки запросов от пользователя на поиск партнера
        """
        self.default_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_EXCHANGE, type="direct"
        )
        main_queue = await self.channel.declare_queue(name=config.RABBITMQ_QUEUE)
        await main_queue.bind(self.default_exchange, config.RABBITMQ_QUEUE)

        """Объявляем обменник и очередь для обрабтки текстовых сообщений от пользователя"""

        self.messages_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_NEW_MESSAGES_EXCHANGE, type="direct"
        )
        new_messages_queue = await self.channel.declare_queue(name=config.RABBITMQ_NEW_MESSAGES_QUEUE)
        await new_messages_queue.bind(self.messages_exchange, config.RABBITMQ_NEW_MESSAGES_QUEUE)

        logger.info(
            f"Queues: {config.RABBITMQ_QUEUE}, {config.RABBITMQ_NEW_USERS_QUEUE}, {config.RABBITMQ_NEW_MESSAGES_QUEUE} "
            f"were successfully declared bount to exchanges: {config.RABBITMQ_EXCHANGE}, {config.RABBITMQ_NEW_USERS_EXCHANGE}, {config.RABBITMQ_NEW_MESSAGES_EXCHANGE}")


    async def publish_message(self, message: "MessageContent"):
        """Публикация сообщения для последующей обработки"""
        await self.messages_exchange.publish(
            aio_pika.Message(
                body=message.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=config.RABBITMQ_NEW_MESSAGES_QUEUE
        )


    async def publish_user(self, user: "NewUser", payment: "NewPayment"):
        """Публикация нового пользователя и транзакции"""
        json_user = json.dumps({
            "purpose": config.ADD_USER_PURPOSE,
            "user": user.model_dump_json(),
            "payment": payment.model_dump_json(),
        }).encode()

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_user, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_NEW_USERS_QUEUE
        )


    async def publish_profile(self, profile: "RegistrationData"):
        json_profile = json.dumps({
            "purpose": config.ADD_PROFILE_PURPOSE,
            "profile": profile.model_dump_json()
        }).encode()

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_profile, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_NEW_USERS_QUEUE
        )


    async def publish_location(self, location: "Location"):
        """Публикация местоположения пользователя"""
        json_location = json.dumps({
            "purpose": config.ADD_LOCATION_PURPOSE,
            "location": location.model_dump_json()
        }).encode()

        await self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_location, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_NEW_USERS_QUEUE
        )

    async def publish_payment(self, payment: "NewPayment"):
        json_payment = json.dumps({
            "purpose": config.ADD_PAYMENT_PURPOSE,
            "payment": payment.model_dump_json()
        }).encode()

        self.new_users_exchange.publish(
            aio_pika.Message(
                body=json_payment, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=config.RABBITMQ_NEW_USERS_QUEUE
        )


    async def publish_request(self, message: "UserMatchRequest"):
        """Публикация запроса на поиск партнера в основную очередь"""
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
