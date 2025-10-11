from typing import TYPE_CHECKING

from app.services.ai_modules import TelegramRateLimiter, ReportDeliveryManager, \
    PendingReportsProcessor, DeepSeekClient, QuestionGenerator, ReportProcessor, WeeklyReportScheduler
from app.services.rabbitmq import rabbitmq_service
from app.services.database import database_service
from app.services.matching import matching_service
from app.services.notification import notification_service
from app.services.redis import redis_service
from app.services.main_bot import main_bot
from app.services.partner_bot import partner_bot
from app.services.yookassa import yookassa_service
from config import config

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from app.services.database import DatabaseService
    from app.services.redis import RedisService
    from app.services.rabbitmq import RabbitMQService
    from app.services.matching import MatchingService
    from app.services.notification import NotificationService
    from app.services.main_bot import MainBot
    from app.services.partner_bot import PartnerBot
    from app.services.yookassa import YookassaService

async def get_main_bot() -> "MainBot":
    if not main_bot.initialized:
        await main_bot.connect()
    return main_bot.get_bot()

async def get_partner_bot() -> "PartnerBot":
    if not partner_bot.initialized:
        await partner_bot.connect()
    return partner_bot.get_bot()


async def get_rabbitmq() -> "RabbitMQService":
    """Зависимость для получения RabbitMQ сервиса"""
    if not rabbitmq_service.connection:
        await rabbitmq_service.connect()

    return rabbitmq_service


async def get_db() -> "DatabaseService":
    """Зависимость для получения подключения к БД"""
    if not database_service.initialized:
        await database_service.connect()
    return database_service


async def get_match() -> "MatchingService":
    """Зависимость для получения Mathcing Service"""
    if not matching_service.redis:
        await matching_service.initialize()
    return matching_service


async def get_notification() -> "NotificationService":
    return notification_service


async def get_redis() -> "RedisService":
    """Зависимость для получения Redis сервиса"""
    if not redis_service.redis_client:
        await redis_service.connect()

    return redis_service


async def get_redis_client() -> "Redis":
    if not redis_service.redis_client:
        await redis_service.connect()

    return redis_service.get_client()


async def get_report_processer() -> "PendingReportsProcessor":
    # Создает объект из AI классов для отправки отчетов
    if not main_bot.initialized:
        await main_bot.connect()
    if not database_service.initialized:
        await database_service.connect()

    bot = main_bot.get_bot()
    tg_rate_limiter = TelegramRateLimiter()
    delivery_manager = ReportDeliveryManager(bot, database_service, tg_rate_limiter)
    pending_report_processer = PendingReportsProcessor(delivery_manager)
    return pending_report_processer


async def generate_notifications() -> "WeeklyReportScheduler":
    # Создает объекты-матрешку из AI классов для генерации отчетов
    deepseek_api_client = DeepSeekClient(api_key=config.AI_API_KEY, base_url=config.AI_API_URL)
    question_generator = QuestionGenerator(deepseek_api_client)
    report_processor = ReportProcessor(question_generator, max_words_per_user=5)
    weekly_report_service = WeeklyReportScheduler(report_processor)
    return weekly_report_service


async def get_yookassa() -> "YookassaService": return yookassa_service