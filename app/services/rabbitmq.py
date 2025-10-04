import json
import logging

import aio_pika

from app.models import Location, UserProfile
from app.models import NewPayment
from app.models import NewUser
from config import config

from typing import TYPE_CHECKING, Optional

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

    async def connect(self):
        """Установка подключения к RabbitMQ"""
        self.connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        # Объявляем обменники и очереди при подключении
        await self.declare_exchanges_and_queues()

    async def declare_exchanges_and_queues(self):
        """Объявление всех обменников и очередей"""
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

        self.new_users_exchange = await self.channel.declare_exchange(
            name=config.RABBITMQ_NEW_USERS_EXCHANGE, type="direct"
        )
        logger.info(f"Exchange declared: {config.RABBITMQ_NEW_USERS_EXCHANGE}")

        new_users_queue = await self.channel.declare_queue(name=config.RABBITMQ_NEW_USERS_QUEUE)
        logger.info(f"Queue declared: {config.RABBITMQ_NEW_USERS_QUEUE}")

        await new_users_queue.bind(self.new_users_exchange, config.RABBITMQ_NEW_USERS_QUEUE)
        logger.info(
            f"Queue {config.RABBITMQ_NEW_USERS_QUEUE} bound to exchange {config.RABBITMQ_NEW_USERS_EXCHANGE} "
            f"with routing key {config.RABBITMQ_NEW_USERS_QUEUE}"
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


    async def publish_profile(self, profile: "UserProfile"):
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



    async def disconnect(self):
        """Закрытие подключения"""
        if self.connection:
            await self.connection.close()


# Глобальный экземпляр сервиса
rabbitmq_service = RabbitMQService()
