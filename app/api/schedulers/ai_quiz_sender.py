import asyncio
import logging
import time

from aiogram import Router, Bot
from aiogram.exceptions import (
    TelegramRetryAfter,
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramServerError,
    TelegramAPIError,
)

from app.bots.main_bot.middlewares.resources_middleware import ResourcesMiddleware
from config import config, LOG_CONFIG

from app.bots.main_bot.keyboards.inline_keyboards import begin_weekly_quiz_keyboard
from app.bots.main_bot.translations import WEEKLY_QUIZ

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="ai_quiz_sender")

router = Router(name=__name__)

TELEGRAM_RETRY_UNTIL_TIME = config.TELEGRAM_RETRY_UNTIL_TIME
TELEGRAM_LAST_REQUEST_TIME = config.AI_LAST_REQUEST_TIME
TELEGRAM_API_SEMAPHORE = config.TELEGRAM_API_SEMAPHORE


async def send_pending_reports(bot, db):
    reports = await db.get_pending_reports()
    if not reports:
        logger.info("Нет ожидающих отчетов")
        return

    logger.info(f"Попытка отправить {len(reports)} ожидающих отчетов.")
    success_count = 0
    failed_reports = []

    # Использование TaskGroup для структурированного параллелизма (Python 3.11+)
    # Это обеспечивает правильную очистку и обработку исключений по задачам.
    async with asyncio.TaskGroup() as tg:
        tasks = []
        for rec in reports:
            task = tg.create_task(
                process_report_delivery(bot, rec["report_id"], rec["user_id"], db)
            )
            tasks.append(task)

        # Ожидание завершения всех задач в TaskGroup
        # TaskGroup обрабатывает исключения, отменяя другие задачи и повторно возбуждая
        # Мы должны явно проверять результаты каждой задачи
        for task in tasks:
            try:
                result = (
                    await task
                )  # Ожидать каждую задачу, чтобы получить ее результат (True/False)
                if result:
                    success_count += 1
                else:
                    # process_report_delivery вернул False, указывая на обработанный сбой
                    # (например, ограничение скорости, пользователь заблокирован, некорректный запрос)
                    # Конкретная причина логируется внутри process_report_delivery
                    failed_reports.append(
                        task.get_name()
                    )  # Или более конкретная информация
            except Exception as e:
                # Этого в идеале не должно происходить, если process_report_delivery обрабатывает ошибки
                # Но это запасной вариант для неожиданных ошибок, распространяющихся из задач
                logger.error(
                    f"Задача по доставке отчета неожиданно завершилась сбоем: {e}",
                    exc_info=True,
                )
                failed_reports.append(task.get_name())

    logger.info(
        f"Отправлено {success_count}/{len(reports)} отчетов. {len(failed_reports)} не удалось отправить."
    )
    if failed_reports:
        logger.warning(f"Детали неудачных отчетов: {failed_reports}")

    # Рассмотреть добавление логики здесь для повторной постановки в очередь неудачных отчетов (не заблокированных/некорректных запросов)
    # для последующей попытки, или оповещения, если постоянные сбои для определенных пользователей.


async def process_report_delivery(
    bot: Bot, report_id: int, user_id: int, db
) -> bool:
    global TELEGRAM_RETRY_UNTIL_TIME, TELEGRAM_LAST_REQUEST_TIME
    async with TELEGRAM_API_SEMAPHORE:
        # Проактивное ограничение скорости: принудительная минимальная задержка между запросами
        # Это помогает избежать превышения лимитов до того, как Telegram отправит 429
        current_time = time.time()
        if (
            current_time - TELEGRAM_LAST_REQUEST_TIME
            < config.TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS
        ):
            wait_time = config.TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS - (
                current_time - TELEGRAM_LAST_REQUEST_TIME
            )
            logger.debug(
                f"Проактивное ограничение скорости Telegram: ожидание {wait_time:.3f}с"
            )
            await asyncio.sleep(wait_time)
        TELEGRAM_LAST_REQUEST_TIME = time.time()

        # Реактивное ограничение скорости: соблюдение глобального retry_after от Telegram
        if time.time() < TELEGRAM_RETRY_UNTIL_TIME:
            sleep_duration = TELEGRAM_RETRY_UNTIL_TIME - time.time()
            logger.warning(
                f"Глобальное ожидание флуда Telegram API: пауза на {sleep_duration:.2f}с для пользователя {user_id}"
            )
            await asyncio.sleep(sleep_duration)

        try:
            # Предполагается, что send_user_report оборачивает bot.send_message и обрабатывает контент
            success = await send_user_report(bot, user_id, report_id, db)
            if success:
                await db.mark_report_as_sent(report_id)
                logger.info(
                    f"Отчет {report_id} успешно отправлен пользователю {user_id}"
                )
                return True
            else:
                # send_user_report вернул False, но исключений не было.
                # Это может указывать на внутренний сбой логики в send_user_report
                logger.error(
                    f"send_user_report вернул False для отчета {report_id}, пользователя {user_id} без возбуждения исключения."
                )
                return False

        except TelegramRetryAfter as e:
            # Это критическая ошибка ограничения скорости
            TELEGRAM_RETRY_UNTIL_TIME = time.time() + e.retry_after
            logger.warning(
                f"Ожидание флуда Telegram API для пользователя {user_id}. "
                f"Повторная попытка через {e.retry_after} секунд. Глобальная пауза принудительно."
            )
            # Не помечать как отправленный, он будет повторно отправлен позже, когда глобальная пауза закончится
            return False  # Указать на неудачу для данной попытки

        except TelegramForbiddenError as e:
            # Бот был заблокирован пользователем или исключен из чата
            logger.warning(
                f"Бот заблокирован пользователем {user_id} (отчет {report_id}): {e.message}. Помечаем пользователя как неактивного."
            )
            await db.mark_user_as_blocked(user_id)  # Требуется новый метод БД
            await db.mark_report_as_sent(
                report_id, status="blocked"
            )  # Пометить как отправленный для удаления из ожидающих, но с конкретным статусом
            return False

        except TelegramBadRequest as e:
            # Указывает на проблему с содержимым сообщения или chat_id
            logger.error(
                f"Некорректный запрос Telegram для пользователя {user_id} (отчет {report_id}): {e.message}. Пропускаем отчет."
            )
            # Это, вероятно, ошибка в промпте/парсинге/логике бота, не временная.
            await db.mark_report_as_sent(report_id, status="bad_request_failed")
            return False

        except (TelegramNetworkError, TelegramServerError) as e:
            # Временные проблемы с сетью или ошибки сервера Telegram
            logger.error(
                f"Временная ошибка Telegram API для пользователя {user_id} (отчет {report_id}): {e}. Повторная попытка позже."
            )
            # Для простой повторной попытки вернуть False. Более продвинутое решение может использовать tenacity здесь.
            return False

        except TelegramAPIError as e:
            # Перехват любых других специфических ошибок Telegram API, не охваченных выше
            logger.error(
                f"Необработанная ошибка Telegram API для пользователя {user_id} (отчет {report_id}): {e}",
                exc_info=True,
            )
            return False

        except Exception as e:
            # Перехват любых других неожиданных ошибок
            logger.critical(
                f"Неожиданная ошибка при доставке отчета для пользователя {user_id} (отчет {report_id}): {e}",
                exc_info=True,
            )
            return False


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
        lang_code = user_info["lang_code"]

        if not report or not words:
            logger.warning(f"No report data found for report_id: {report_id}")
            return False

        # Извлекаем ID отправленного сообщения
        await bot.send_message(
            chat_id=user_id,
            text=WEEKLY_QUIZ["weekly_report"][lang_code].format(total=len(words)),
            reply_markup=begin_weekly_quiz_keyboard(lang_code, report_id),
        )

        return True

    except TelegramForbiddenError:
        raise
    except TelegramBadRequest:
        raise

    except Exception as e:
        logger.error(
            f"Ошибка при отправке отчета {report_id} пользователю {user_id}: {e}",
            exc_info=True,
        )
        return False
