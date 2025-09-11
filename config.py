import os
import sys
import logging
from asyncio import Semaphore
from dataclasses import dataclass

from dotenv import load_dotenv

# Определите путь относительно текущего файла
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

# Logging configurations
LOG_CONFIG = {
    "level": logging.INFO,
    "stream": sys.stdout,
    "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
}


@dataclass
class Config:
    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    RABBITMQ_QUEUE: str = os.getenv("RABBITMQ_QUEUE", "default")
    RABBITMQ_EXCHANGE: str = os.getenv("RABBITMQ_EXCHANGE", "users")

    RABBITMQ_DELAYED_EXCHANGE: str = os.getenv("RABBITMQ_DELAYED_EXCHANGE", "none")
    RABBITMQ_DELAYED_QUEUE: str = os.getenv("RABBITMQ_DELAYED_QUEUE", "none")

    # URL разных запросов
    NOTIFICATION_URL: str = os.getenv("NOTIFICATION_URL", "0.0.0.0:8000")
    # PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:pass@localhost:5432/db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Telegram Bot
    BOT_TOKEN_MAIN: str = os.getenv("BOT_TOKEN_MAIN")
    BOT_TOKEN_PARTNER: str = os.getenv("BOT_TOKEN_PARTNER")

    # Глобальные переменные для ограничения запросов
    REQUEST_SEMAPHORE = Semaphore(3)
    REQUEST_RATE_LIMITER = Semaphore(50)

    AI_LAST_REQUEST_TIME = 0.0
    # Глобальная метка времени для паузы всех вызовов Telegram API
    TELEGRAM_API_SEMAPHORE = Semaphore(5)
    # Глобальная метка времени для паузы всех вызовов Telegram API
    TELEGRAM_RETRY_UNTIL_TIME = 0.0
    # Для принудительного соблюдения лимитов в секунду при необходимости
    TELEGRAM_LAST_REQUEST_TIME = 0.0
    # Для проактивного лимита 20 сообщений/сек (1/20)
    TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS = 0.05

    # Версия FRONTEND
    VERSION = "20250826-3"

    # ID админа
    ADMIN_ID: int = os.getenv("ADMIN_ID", 0)

    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret_key")


config = Config()
