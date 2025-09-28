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