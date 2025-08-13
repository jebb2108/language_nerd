import logging
import sys
import asyncio
import random
import aiohttp
import time
import re
from datetime import datetime
from typing import List

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)

from aiogram import Bot

from aiogram.exceptions import (
    TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError,
    TelegramNetworkError, TelegramBadRequest, TelegramServerError,
)

from middlewares.resources_middleware import ResourcesMiddleware
from routers.commands.weekly_message_commands import send_user_report
from utils.database import ReportDatabase
from config import (
    AI_API_KEY,
    AI_API_URL,
    BOT_TOKEN_MAIN,
    REQUEST_SEMAPHORE,
    REQUEST_RATE_LIMITER,
    TELEGRAM_API_SEMAPHORE,
    AI_LAST_REQUEST_TIME,
    TELEGRAM_RETRY_UNTIL_TIME,
    TELEGRAM_LAST_REQUEST_TIME,
    TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS,
    DEFAULT_DEEPSEEK_URL,
    LOG_CONFIG,
)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='ai_handler')

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def should_retry_api_error(result):
    """Определяет, нужно ли повторять запрос при ошибке API"""
    return result is None


def is_payment_required_error(exception):
    """Проверяет, является ли ошибка Payment Required (402)"""
    if isinstance(exception, aiohttp.ClientResponseError):
        return exception.status == 402
    return False


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    retry=(
                  retry_if_exception_type(aiohttp.ClientResponseError) &
                  retry_if_result(lambda e: not is_payment_required_error(e))
          ) | retry_if_result(should_retry_api_error),
    reraise=True
)
async def generate_question_for_word(word, session):
    """Генерирует вопрос с вариантами ответов для слова с использованием DeepSeek"""

    global AI_LAST_REQUEST_TIME

    word_str = str(word).strip()
    if not word_str:
        return None

    # Формируем промпт для DeepSeek
    safe_word = word_str.replace("'", "\\'").replace('"', '\\"')
    prompt = (
        f"Создай вопрос для проверки знания слова '{safe_word}'. "
        "Придумай предложение, где вместо этого слова стоит троеточие. "
        "Предоставь один правильный вариант ответа и три неправильных, "
        "но похожих по значению. Варианты должны быть в случайном порядке.\n\n"
        "Формат ответа:\n"
        "Предложение: [предложение с ...]\n"
        "Варианты: [правильный, неправильный1, неправильный2, неправильный3]\n\n"
        "ВАЖНО: Не добавляй дополнительные пояснения, комментарии или разметку!"
    )

    async with REQUEST_SEMAPHORE:
        async with REQUEST_RATE_LIMITER:
            current_time = time.time()
            if current_time - AI_LAST_REQUEST_TIME < 1.2:
                wait_time = 1.2 - (current_time - AI_LAST_REQUEST_TIME)
                await asyncio.sleep(wait_time)

            try:
                # Обработка случая, когда AI_API_URL не задан
                if AI_API_URL is None:
                    logger.warning("AI_API_URL is None, using default DeepSeek URL")
                    api_url = DEFAULT_DEEPSEEK_URL
                elif not isinstance(AI_API_URL, str):
                    logger.warning(f"AI_API_URL is not a string! Type: {type(AI_API_URL)}, Value: {AI_API_URL}")
                    api_url = DEFAULT_DEEPSEEK_URL
                else:
                    api_url = AI_API_URL.strip()

                # Формируем запрос для DeepSeek API
                async with session.post(
                        api_url,
                        headers={
                            "Authorization": f"Bearer {AI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "Ты полезный помощник для изучения английского языка. Отвечай строго в указанном формате без дополнительных пояснений."
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ],
                            "temperature": 0.7,
                            "max_tokens": 1024,
                            "frequency_penalty": 0,
                            "presence_penalty": 0,
                            "stop": None
                        },
                        timeout=60
                ) as response:
                    AI_LAST_REQUEST_TIME = time.time()

                    # Обработка rate limit
                    if response.status == 429:
                        retry_after = response.headers.get('Retry-After', '5')
                        try:
                            retry_after = float(retry_after)
                        except ValueError:
                            retry_after = 5

                        logger.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=429,
                            message='Too Many Requests',
                            headers=response.headers
                        )

                    # Обработка ошибки оплаты
                    if response.status == 402:
                        logger.critical("DeepSeek API requires payment. Please upgrade your account.")
                        return None

                    response.raise_for_status()
                    data = await response.json()


                    # Извлекаем ответ из DeepSeek
                    content = data['choices'][0]['message']['content'].strip()
                    return parse_deepseek_response(content, safe_word)
            except aiohttp.ClientResponseError as e:
                if e.status == 402:
                    logger.critical("DeepSeek API requires payment. Please upgrade your account.")
                    return None
                elif e.status == 429:
                    logger.error(f"Rate limit exceeded for '{safe_word}'. Headers: {e.headers}")
                raise
            except Exception as e:
                logger.error(f"DeepSeek API error for '{safe_word}': {e}", exc_info=True)
                return None


def parse_deepseek_response(content, original_word):
    """Парсит ответ от DeepSeek в нужный формат"""
    try:
        # Убираем лишнее форматирование (*, [], (), кавычки)
        cleaned_content = re.sub(r'\*|\[.*?\]|\(.*?\)', '', content)

        # Разбиваем на строки и очищаем пробелы
        lines = [line.strip() for line in cleaned_content.split('\n') if line.strip()]

        sentence = None
        options = []

        # --- Поиск предложения с "..." ---
        for line in lines:
            if "..." in line:
                sentence = re.sub(r'^(предложение|sentence):\s*', '', line, flags=re.IGNORECASE).strip().strip('"').strip("'")
                break

        # Если не нашли — берём первую строку
        if not sentence and lines:
            sentence = lines[0]

        # --- Поиск вариантов ---
        for i, line in enumerate(lines):
            if re.match(r'^(варианты|options):', line, re.IGNORECASE):
                # Забираем всё, что после двоеточия
                after_colon = re.sub(r'^(варианты|options):\s*', '', line, flags=re.IGNORECASE)
                if after_colon:
                    # Если варианты в одну строку через запятую
                    inline_opts = [opt.strip() for opt in after_colon.split(',') if opt.strip()]
                    options.extend(inline_opts)

                # Если модель выдала варианты в следующих строках
                for j in range(i + 1, min(i + 6, len(lines))):
                    opt_line = lines[j].strip()
                    if opt_line:
                        clean_option = re.sub(r'^[-\*]?\s*\d?\.?\s*', '', opt_line).strip()
                        if clean_option:
                            options.append(clean_option)
                break

        # --- Если метки "Варианты:" нет, ищем список из 4+ элементов ---
        if not options:
            candidate_options = []
            for line in lines:
                if line == sentence:
                    continue
                clean_option = re.sub(r'^[-\*]?\s*\d?\.?\s*', '', line).strip()
                if clean_option:
                    candidate_options.append(clean_option)
            if len(candidate_options) >= 4:
                options = candidate_options[:4]

        # --- Проверки ---
        if not sentence:
            logger.warning(f"Не найдено предложение в ответе: {content}")
            return None

        if len(options) < 4:
            logger.warning(f"Недостаточно вариантов в ответе (найдено {len(options)}): {content}")
            return None

        options = options[:4]

        # Проверяем, есть ли оригинальное слово среди вариантов
        if original_word.lower() not in [opt.lower() for opt in options]:
            logger.warning(f"Original word '{original_word}' not found in options: {options}")
            return None

        return {"sentence": sentence, "options": options}

    except Exception as e:
        logger.error(f"Parse error for '{original_word}': {e}", exc_info=True)
        return None



# ========== ОСНОВНЫЕ ФУНКЦИИ ОБРАБОТКИ ==========
async def process_user_report(user_id: int, words: List[str], session, db: ReportDatabase) -> int:
    """Обрабатывает отчет для одного пользователя"""

    if await db.is_user_blocked(user_id):
        logger.info(f"User {user_id} is blocked — skipping report generation")
        return False

    report_data = []

    for word in words:
        word_str = str(word).strip()
        if not word_str:
            continue

        try:
            question_data = await generate_question_for_word(word_str, session)
        except Exception as e:
            logger.error(f"Failed to generate question for '{word_str}': {e}")
            question_data = None

        if not question_data:
            continue

        options = question_data["options"].copy()
        random.shuffle(options)

        try:
            # Поиск правильного ответа без учета регистра
            correct_index = next(i for i, opt in enumerate(question_data["options"])
                                 if opt.lower() == word_str.lower())

            report_data.append({
                "word": word_str,
                "sentence": question_data["sentence"],
                "options": options,
                "correct_index": correct_index
            })
        except (ValueError, StopIteration):
            logger.warning(f"Correct word '{word_str}' not found in options: {question_data['options']}")

    # Сохраняем отчет в БД
    if report_data:
        async with db.acquire_connection() as conn:
            async with conn.transaction():
                report_id = await db.create_report(user_id)
                await db.add_words_to_report(report_id, report_data)

    logger.info(f"Generated report for user {user_id} with {len(report_data)} words")
    return len(report_data)


async def generate_weekly_reports(db: ReportDatabase, session):
    """Генерирует недельные отчеты с ограничением скорости"""
    user_words = await db.get_weekly_words_by_user()

    if not user_words:
        logger.info("No users with enough words")
        return

    max_words_per_user = 5
    max_users_per_minute = 3
    processed_users = 0
    start_time = datetime.now()

    for record in user_words:
        user_id = record["user_id"]

        # --- Патч: пропустить заблокированных пользователей ---
        if await db.is_user_blocked(user_id):
            logger.info(f"Skipping generation for blocked user {user_id}")
            continue

        words = record["words"]

        selected_words = random.sample(words, min(len(words), max_words_per_user))
        words_processed = await process_user_report(user_id, selected_words, session, db)

        # Если не удалось обработать ни одного слова, пропускаем пользователя
        if words_processed == 0:
            logger.warning(f"Skipping user {user_id} - no questions generated")
            continue

        processed_users += 1

        # Контроль скорости обработки
        elapsed = (datetime.now() - start_time).total_seconds()
        required_delay = max(0, (60 / max_users_per_minute) - elapsed)
        if required_delay > 0:
            logger.info(f"Rate limiting: waiting {required_delay:.1f}s before next user")
            await asyncio.sleep(required_delay)
            start_time = datetime.now()
        else:
            start_time = datetime.now()

    logger.info(f"Generated reports for {processed_users} users")


async def send_pending_reports(bot: Bot, db: ReportDatabase):
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
            task = tg.create_task(process_report_delivery(bot, rec["report_id"], rec["user_id"], db))
            tasks.append(task)

        # Ожидание завершения всех задач в TaskGroup
        # TaskGroup обрабатывает исключения, отменяя другие задачи и повторно возбуждая
        # Мы должны явно проверять результаты каждой задачи
        for task in tasks:
            try:
                result = await task # Ожидать каждую задачу, чтобы получить ее результат (True/False)
                if result:
                    success_count += 1
                else:
                    # process_report_delivery вернул False, указывая на обработанный сбой
                    # (например, ограничение скорости, пользователь заблокирован, некорректный запрос)
                    # Конкретная причина логируется внутри process_report_delivery
                    failed_reports.append(task.get_name()) # Или более конкретная информация
            except Exception as e:
                # Этого в идеале не должно происходить, если process_report_delivery обрабатывает ошибки
                # Но это запасной вариант для неожиданных ошибок, распространяющихся из задач
                logger.error(f"Задача по доставке отчета неожиданно завершилась сбоем: {e}", exc_info=True)
                failed_reports.append(task.get_name())

    logger.info(f"Отправлено {success_count}/{len(reports)} отчетов. {len(failed_reports)} не удалось отправить.")
    if failed_reports:
        logger.warning(f"Детали неудачных отчетов: {failed_reports}")

    # Рассмотреть добавление логики здесь для повторной постановки в очередь неудачных отчетов (не заблокированных/некорректных запросов)
    # для последующей попытки, или оповещения, если постоянные сбои для определенных пользователей.


async def process_report_delivery(bot: Bot, report_id: int, user_id: int, db: ReportDatabase) -> bool:
    global TELEGRAM_RETRY_UNTIL_TIME, TELEGRAM_LAST_REQUEST_TIME
    async with TELEGRAM_API_SEMAPHORE:
        # Проактивное ограничение скорости: принудительная минимальная задержка между запросами
        # Это помогает избежать превышения лимитов до того, как Telegram отправит 429
        current_time = time.time()
        if current_time - TELEGRAM_LAST_REQUEST_TIME < TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS:
            wait_time = TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS - (current_time - TELEGRAM_LAST_REQUEST_TIME)
            logger.debug(f"Проактивное ограничение скорости Telegram: ожидание {wait_time:.3f}с")
            await asyncio.sleep(wait_time)
        TELEGRAM_LAST_REQUEST_TIME = time.time()

        # Реактивное ограничение скорости: соблюдение глобального retry_after от Telegram
        if time.time() < TELEGRAM_RETRY_UNTIL_TIME:
            sleep_duration = TELEGRAM_RETRY_UNTIL_TIME - time.time()
            logger.warning(f"Глобальное ожидание флуда Telegram API: пауза на {sleep_duration:.2f}с для пользователя {user_id}")
            await asyncio.sleep(sleep_duration)

        try:
            # Предполагается, что send_user_report оборачивает bot.send_message и обрабатывает контент
            success = await send_user_report(bot, user_id, report_id, db)
            if success:
                await db.mark_report_as_sent(report_id)
                logger.info(f"Отчет {report_id} успешно отправлен пользователю {user_id}")
                return True
            else:
                # send_user_report вернул False, но исключений не было.
                # Это может указывать на внутренний сбой логики в send_user_report
                logger.error(f"send_user_report вернул False для отчета {report_id}, пользователя {user_id} без возбуждения исключения.")
                return False

        except TelegramRetryAfter as e:
            # Это критическая ошибка ограничения скорости
            TELEGRAM_RETRY_UNTIL_TIME = time.time() + e.retry_after
            logger.warning(
                f"Ожидание флуда Telegram API для пользователя {user_id}. "
                f"Повторная попытка через {e.retry_after} секунд. Глобальная пауза принудительно."
            )
            # Не помечать как отправленный, он будет повторно отправлен позже, когда глобальная пауза закончится
            return False # Указать на неудачу для данной попытки

        except TelegramForbiddenError as e:
            # Бот был заблокирован пользователем или исключен из чата
            logger.warning(f"Бот заблокирован пользователем {user_id} (отчет {report_id}): {e.message}. Помечаем пользователя как неактивного.")
            await db.mark_user_as_blocked(user_id) # Требуется новый метод БД
            await db.mark_report_as_sent(report_id, status='blocked') # Пометить как отправленный для удаления из ожидающих, но с конкретным статусом
            return False

        except TelegramBadRequest as e:
            # Указывает на проблему с содержимым сообщения или chat_id
            logger.error(f"Некорректный запрос Telegram для пользователя {user_id} (отчет {report_id}): {e.message}. Пропускаем отчет.")
            # Это, вероятно, ошибка в промпте/парсинге/логике бота, не временная.
            await db.mark_report_as_sent(report_id, status='bad_request_failed')
            return False

        except (TelegramNetworkError, TelegramServerError) as e:
            # Временные проблемы с сетью или ошибки сервера Telegram
            logger.error(f"Временная ошибка Telegram API для пользователя {user_id} (отчет {report_id}): {e}. Повторная попытка позже.")
            # Для простой повторной попытки вернуть False. Более продвинутое решение может использовать tenacity здесь.
            return False

        except TelegramAPIError as e:
            # Перехват любых других специфических ошибок Telegram API, не охваченных выше
            logger.error(f"Необработанная ошибка Telegram API для пользователя {user_id} (отчет {report_id}): {e}", exc_info=True)
            return False

        except Exception as e:
            # Перехват любых других неожиданных ошибок
            logger.critical(f"Неожиданная ошибка при доставке отчета для пользователя {user_id} (отчет {report_id}): {e}", exc_info=True)
            return False

async def cleanup_old_reports(db: ReportDatabase, days: int = 30) -> bool:
    """Очищает старые отчеты и связанные с ними данные"""
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


# ========== ТОЧКА ВХОДА ==========
async def main():
    """Основная асинхронная точка входа"""
    bot = None
    resources = ResourcesMiddleware()
    await resources.on_startup()

    try:
        # Инициализируем базу данных для отчетов
        db = ReportDatabase(resources.db_pool)
        session = resources.session

        if '--generate' in sys.argv:
            logger.info("Generating weekly reports with DeepSeek...")
            await generate_weekly_reports(db, session)
        elif '--cleanup' in sys.argv:
            logger.info("Cleaning up old reports...")
            await cleanup_old_reports(db, days=30)
        else:
            logger.info("Sending pending reports...")
            bot = Bot(token=BOT_TOKEN_MAIN)
            await send_pending_reports(bot, db)

    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)

    finally:
        if bot: await bot.session.close()
        await resources.on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
