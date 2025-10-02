import asyncio
from app.dependencies import get_report_processer
from config import config
from logging_config import opt_logger as log

# Настройка логирования
logger = log.setup_logger('schedulers', config.LOG_LEVEL)


async def main() -> None:
    weekly_report_scheduler = await get_report_processer()
    await weekly_report_scheduler.generate_weekly_reports()
    return

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    asyncio.run(main())
