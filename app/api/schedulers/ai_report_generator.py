import logging
import asyncio

from config import LOG_CONFIG
from app.dependencies import get_report_processer

# Настройка логирования
logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="schedulers")


async def main() -> None:
    weekly_report_scheduler = get_report_processer()
    await weekly_report_scheduler.generate_weekly_reports()
    return

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    asyncio.run(main())
