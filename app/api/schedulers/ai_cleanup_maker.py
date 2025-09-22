import asyncio
import logging
from app.dependencies import get_db
from config import LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='ai_cleanup_maker')


async def cleanup_old_reports(days: int = 30) -> bool:
    """Очищает старые отчеты и связанные с ними данные"""
    db = await get_db()
    try:
        logger.info(f"Starting cleanup for reports older than {days} days")
        reports_deleted, words_deleted = await db.cleanup_old_reports(days)

        logger.info(
            f"Cleaned up {reports_deleted} reports and "
            f"{words_deleted} words older than {days} days"
        )
        return True
    except Exception as e:
        logger.error(f"Error cleaning old reports: {e}")
        return False

if __name__ == '__main__':
    asyncio.run(cleanup_old_reports())
