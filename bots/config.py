import os
import sys
import logging
from dotenv import load_dotenv
from asyncio import Semaphore

load_dotenv(".env")

# Конфигурация
BOT_TOKEN_MAIN = os.getenv('BOT_TOKEN_MAIN')
BOT_TOKEN_PARTNER = os.getenv('BOT_TOKEN_PARTNER')

AI_API_URL = os.getenv('AI_API_URL')
AI_API_KEY = os.getenv('AI_API_KEY')

# Значение по умолчанию для DeepSeek API
DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# Настройка логирования
LOG_CONFIG = {
    'level': logging.INFO,
    'stream': sys.stdout,
    'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
}

# Конфигурация базы данных
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5433")),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
    "database": os.getenv("POSTGRES_DB", "telegram_bot"),
}

# Глобальные переменные для ограничения запросов
REQUEST_SEMAPHORE = Semaphore(3)
REQUEST_RATE_LIMITER = Semaphore(50)

AI_LAST_REQUEST_TIME = 0.0

TELEGRAM_API_SEMAPHORE = Semaphore(5)
TELEGRAM_RETRY_UNTIL_TIME = 0.0 # Глобальная метка времени для паузы всех вызовов Telegram API
TELEGRAM_LAST_REQUEST_TIME = 0.0 # Для принудительного соблюдения лимитов в секунду при необходимости
TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS = 0.05 # Для проактивного лимита 20 сообщений/сек (1/20)