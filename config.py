import os
import sys
import logging
from asyncio import Semaphore
from dataclasses import dataclass
from datetime import timezone, timedelta

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

LANG_CODE_LIST: list = list(["en", "ru", "de", "es", "zh"])


@dataclass
class Config:
    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    # RABBITMQ_QUEUE: str = os.getenv("RABBITMQ_QUEUE", "default")
    RABBITMQ_QUEUE: str = os.getenv("RABBITMQ_ROUTING_KEY", "queue")
    RABBITMQ_EXCHANGE: str = os.getenv("RABBITMQ_EXCHANGE", "exchange")

    # PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:pass@localhost:5432/db"
    )

    BASE_URL: str = os.getenv("BASE_DOMAIN", "localhost")
    # BASE_PORT: int = int(os.getenv("BASE_PORT", 1000))
    WEB_SERVER_PORT: int = int(os.getenv("WEB_SERVER_PORT", 2000))
    CHAT_SERVER_PORT: int = int(os.getenv("CHAT_SERVER_PORT", 3000))


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
    VERSION = "20250826-4"

    # ID админа
    ADMIN_ID: int = os.getenv("ADMIN_ID", 0)

    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret_key")

    TZINFO = timezone(timedelta(hours=0.0))

    SEARCH_STARTED = 'search_started'
    SEARCH_CANCELED = 'search_canceled'
    SEARCH_COMPLETED = 'search_completed'

    ABS_PATH_TO_IMG_ONE: str = os.getenv("ABS_PATH_TO_IMG_ONE", '/')
    ABS_PATH_TO_IMG_TWO: str = os.getenv("ABS_PATH_TO_IMG_TWO", '/')
    ABS_PATH_TO_CHAT_INDX: str = os.getenv("ABS_PATH_TO_CHAT_INDX", '/')

    WAIT_TIMER: int = 150
    SLEEP_TIME: int = 5


config = Config()
