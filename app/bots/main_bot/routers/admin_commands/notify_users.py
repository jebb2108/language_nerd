from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from app.dependencies import get_db, get_report_processer
from config import config
from app.services.ai_modules import ReportDeliveryManager, TelegramRateLimiter, PendingReportsProcessor
from logging_config import opt_logger as log


logger = log.setup_logger('send_pending_handler')

router = Router(name=__name__)

@router.message(
    Command("notify_users", prefix="!"),
    lambda message: message.from_user.id == int(config.ADMIN_ID)
)
async def notify_users(message: Message):
    database = await get_db()
    all_users = await database.get_all_users()
    pending_report_processer = await get_report_processer()
    results: dict = await pending_report_processer.process_all_pending_reports()
    msg = "Привет! Давно тебя не видела :( Начни добавлять слова, чтобы быть the best"
    for user in all_users:
        if user not in results["success_ids"]:
            await message.bot.send_message(chat_id=user, text=msg)

    await message.answer(
        f"reports sent: {results["success_count"]}\n"
        f"failed reports: {results["failed_count"]}\n"
        f"detailed: {results["failed_reports"]}"
    )


