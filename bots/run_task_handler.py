import sys
import asyncio
import logging
import aiohttp
import os
from datetime import datetime
from config import LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='run_task_handler')


async def send_command_to_bot(command='!send_reports'):
    bot_token = os.getenv('BOT_TOKEN_MAIN')
    chat_id = os.getenv('ADMIN_ID')

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': command
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            if resp.status == 200:
                 logger.info(f"Command sent at: {datetime.now()}")
            else:
                logger.error(f"Error while sending command. Code status: %s", resp.status)


async def main():
    """Основная асинхронная точка входа"""
    try:
        if '--generate' in sys.argv:
            logger.info("Generating weekly reports with DeepSeek...")
            await send_command_to_bot('!generate_reports')
        elif '--cleanup' in sys.argv:
            logger.info("Cleaning up old reports...")
            await send_command_to_bot('!clean_up_reports')
        else:
            await send_command_to_bot()


    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)



if __name__ == "__main__":
    asyncio.run(main())
