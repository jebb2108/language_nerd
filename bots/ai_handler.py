import sys
import asyncio
import random
import aiohttp
import time
import re
from datetime import datetime, timedelta
from typing import List

import asyncpg
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)

from aiogram import Bot

from middlewares.resources_middleware import ResourcesMiddleware
from routers.commands.weekly_message_commands import send_user_report
from utils.database import ReportDatabase
from config import (
    AI_API_KEY,
    AI_API_URL,
    BOT_TOKEN_MAIN,
    logger,
)

# Глобальные переменные для ограничения запросов
REQUEST_SEMAPHORE = asyncio.Semaphore(3)
REQUEST_RATE_LIMITER = asyncio.Semaphore(50)
last_request_time = 0

# Значение по умолчанию для DeepSeek API
DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


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
    global last_request_time

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
            if current_time - last_request_time < 1.2:
                wait_time = 1.2 - (current_time - last_request_time)
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
                    last_request_time = time.time()

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
        # Удаляем лишние символы форматирования
        cleaned_content = re.sub(r'\*|\(.*?\)|\[.*?\]', '', content)

        # Ищем предложение и варианты с более гибким распознаванием
        sentence = None
        options = []

        # Разбиваем содержимое на строки и очищаем
        lines = [line.strip() for line in cleaned_content.split('\n') if line.strip()]

        # Ищем предложение по наличию троеточия
        for i, line in enumerate(lines):
            if "..." in line:
                # Удаляем метки "Предложение:" если есть
                sentence = re.sub(r'^(предложение|sentence):\s*', '', line, flags=re.IGNORECASE).strip()
                # Удаляем лишние пробелы и кавычки
                sentence = sentence.strip().strip('"').strip("'")
                break

        # Если не нашли предложение с троеточием, используем первую строку
        if not sentence and lines:
            sentence = lines[0]

        # Ищем варианты ответов
        for i, line in enumerate(lines):
            if re.match(r'^(варианты|options):', line, re.IGNORECASE):
                # Собираем следующие строки как варианты
                for j in range(i + 1, min(i + 5, len(lines))):
                    option_line = lines[j].strip()
                    if option_line:
                        # Удаляем маркеры списка и номера
                        clean_option = re.sub(r'^[-\*]?\s*\d?\.?\s*', '', option_line)
                        # Удаляем пометки в скобках
                        clean_option = re.sub(r'\(.*?\)', '', clean_option).strip()
                        options.append(clean_option)
                break

        # Если не нашли метку вариантов, ищем список из 4 элементов
        if not options:
            candidate_options = []
            for line in lines:
                # Пропускаем строку с предложением
                if line == sentence:
                    continue
                # Удаляем маркеры списка и номера
                clean_option = re.sub(r'^[-\*]?\s*\d?\.?\s*', '', line).strip()
                # Удаляем пометки в скобках
                clean_option = re.sub(r'\(.*?\)', '', clean_option).strip()
                if clean_option:
                    candidate_options.append(clean_option)

            # Если нашли ровно 4 варианта, используем их
            if len(candidate_options) >= 4:
                options = candidate_options[:4]

        # Проверяем наличие всех необходимых элементов
        if not sentence:
            logger.warning(f"Не найдено предложение в ответе: {content}")
            return None

        if not options or len(options) < 4:
            logger.warning(f"Недостаточно вариантов в ответе (найдено {len(options)}): {content}")
            return None

        # Берем только первые 4 варианта
        options = options[:4]

        # Проверяем наличие оригинального слова в вариантах (без учета регистра)
        original_lower = original_word.lower()
        options_lower = [opt.lower() for opt in options]

        if original_lower not in options_lower:
            logger.warning(f"Original word '{original_word}' not found in options: {options}")
            return None

        # Возвращаем варианты в оригинальном регистре
        return {"sentence": sentence, "options": options}
    except Exception as e:
        logger.error(f"Parse error for '{original_word}': {e}", exc_info=True)
        return None


# ========== ОСНОВНЫЕ ФУНКЦИИ ОБРАБОТКИ ==========
async def process_user_report(user_id: int, words: List[str], session, db: ReportDatabase) -> int:
    """Обрабатывает отчет для одного пользователя"""
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

        try:
            # Поиск правильного ответа без учета регистра
            correct_index = next(i for i, opt in enumerate(question_data["options"])
                                 if opt.lower() == word_str.lower())

            report_data.append({
                "word": word_str,
                "sentence": question_data["sentence"],
                "options": question_data["options"],
                "correct_index": correct_index
            })
        except (ValueError, StopIteration):
            logger.warning(f"Correct word '{word_str}' not found in options: {question_data['options']}")

        # Задержка для соблюдения rate limit
        delay = 2.0 + random.random() * 3.0
        await asyncio.sleep(delay)

    # Сохраняем отчет в БД
    if report_data:
        async with db.db_pool.acquire() as conn:
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
        words = record["words"]
        user_id = record["user_id"]

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
        logger.info("No pending reports")
        return

    tasks = [
        process_report_delivery(bot, rec["report_id"], rec["user_id"], db)
        for rec in reports
    ]
    results = await asyncio.gather(*tasks)
    success_count = sum(1 for r in results if r)
    logger.info(f"Sent {success_count}/{len(reports)} reports")


async def process_report_delivery(bot: Bot, report_id: int, user_id: int, db: ReportDatabase) -> bool:
    success = await send_user_report(bot, user_id, report_id)
    if success:
        await db.mark_report_as_sent(report_id)
    return success


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
            await cleanup_old_reports(db, days=14)
        else:
            logger.info("Sending pending reports...")
            bot = Bot(token=BOT_TOKEN_MAIN)
            await send_pending_reports(bot, db)

    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)

    finally:
        await resources.on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
