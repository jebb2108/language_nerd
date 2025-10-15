import asyncio
from app.dependencies import generate_notifications
from logging_config import opt_logger as log

# Настройка логирования
logger = log.setup_logger('schedulers')


async def main() -> None:
    weekly_report_scheduler = await generate_notifications()
    await weekly_report_scheduler.generate_reports()
    return

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    asyncio.run(main())
