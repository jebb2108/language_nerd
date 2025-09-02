import logging

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from middlewares.resources_middleware import ResourcesMiddleware # noqa
from keyboards.inline_keyboards import begin_weekly_quiz_keyboard # noqa
from config import LOG_CONFIG # noqa

from translations import WEEKLY_QUIZ # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='weekly_message_commands')

# Инициализация роутера
router = Router(name=__name__)


@router.message(Command('weekly_task', prefix='!'))
async def send_user_report(
        bot: Bot,
        user_id: int,
        report_id: int,
        database: ResourcesMiddleware,
) -> bool:
    """
    Отправляет пользователю его еженедельный отчет.
    """
    try:
        report = await database.get_report(report_id)
        words = await database.get_weekly_words(report_id)
        user_info = await database.get_user_info(user_id)
        lang_code = user_info['lang_code']

        if not report or not words:
            logger.warning(f"No report data found for report_id: {report_id}")
            return False

        # Извлекаем ID отправленного сообщения
        await bot.send_message(
            chat_id=user_id,
            text=WEEKLY_QUIZ['weekly_report'][lang_code].format(total=len(words)),
            reply_markup=begin_weekly_quiz_keyboard(lang_code, report_id)
        )

        return True

    except TelegramForbiddenError:
        raise
    except TelegramBadRequest:
        raise

    except Exception as e:
        logger.error(f"Ошибка при отправке отчета {report_id} пользователю {user_id}: {e}", exc_info=True)
        return False