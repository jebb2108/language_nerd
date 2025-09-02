# send_command.py
import logging
import aiohttp
import os
from datetime import datetime
from config import LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='weekly_ai_script')


def send_command_to_bot():
    bot_token = os.getenv('BOT_TOKEN_MAIN')
    chat_id = os.getenv('ADMIN_ID')
    command = "!weekly_task"  # Команда, которую бот должен выполнить

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


if __name__ == "__main__":
    send_command_to_bot()