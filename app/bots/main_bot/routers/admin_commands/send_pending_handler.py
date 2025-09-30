import logging

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from app.dependencies import get_db
from config import LOG_CONFIG, config
from app.services.ai_modules import ReportDeliveryManager, TelegramRateLimiter, PendingReportsProcessor


# ========== COMPATIBILITY FUNCTIONS ==========
async def send_pending_reports(bot, db) -> None:
    """
    Отправляет ожидающие отчеты
    (Функция для обратной совместимости)
    """
    tg_rate_limiter = TelegramRateLimiter()
    delivery_manager = ReportDeliveryManager(bot, db, tg_rate_limiter)
    pending_report_processer = PendingReportsProcessor(delivery_manager)
    await pending_report_processer.process_all_pending_reports()

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="send_pending_handler")

router = Router(name=__name__)

@router.message(
    Command("send_pending", prefix="!"),
    lambda message: message.from_user.id == int(config.ADMIN_ID)
)
async def send_pending(message: Message):
    database = await get_db()
    tg_rate_limiter = TelegramRateLimiter()
    delivery_manager = ReportDeliveryManager(message.bot, database, tg_rate_limiter)
    pending_report_processer = PendingReportsProcessor(delivery_manager)
    results: dict = await pending_report_processer.process_all_pending_reports()
    msg = ''.join([f"{k}: {v}\n" for k, v in results.items()])
    await message.answer(msg)


