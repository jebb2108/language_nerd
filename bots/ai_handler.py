import sys
import asyncio
import random
import aiohttp
import time
import re
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_result

# Предполагается, что эти импорты доступны в вашем проекте
from routers.commands.weekly_message_commands import send_user_report
from config import (
    AI_API_KEY,
    AI_API_URL,
    init_global_resources,
    close_global_resources,
    logger
)

# Глобальные переменные для ограничения запросов
REQUEST_SEMAPHORE = asyncio.Semaphore(3)
REQUEST_RATE_LIMITER = asyncio.Semaphore(50)
last_request_time = 0

# Значение по умолчанию для DeepSeek API
DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


async def get_weekly_words_by_user(db_pool):
    """Получает слова за неделю, сгруппированные по пользователям"""
    query = """
        SELECT user_id, ARRAY_AGG(DISTINCT word) as words
        FROM words
        WHERE created_at <= $1 AND word IS NOT NULL
        GROUP BY user_id
        HAVING COUNT(word) > 1
    """
    week_ago = datetime.now() - timedelta(days=7)
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, week_ago)


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
        cleaned_content = re.sub(r'\*|\#|\(.*?\)|\[.*?\]', '', content)

        # Ищем предложение и варианты с более гибким распознаванием
        sentence = None
        options = []

        # Пытаемся найти предложение в разных форматах
        for line in cleaned_content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Распознаем предложение по ключевым словам или структуре
            if line.lower().startswith("предложение:") or "..." in line:
                # Удаляем метку "Предложение:" если есть
                sentence = re.sub(r'^(предложение|sentence):\s*', '', line, flags=re.IGNORECASE).strip()
            # Распознаем варианты по ключевым словам или формату списка
            elif line.lower().startswith("варианты:") or line.lower().startswith("options:") or re.match(
                    r'^[\-\*]?\s*\w', line):
                # Удаляем метку "Варианты:" если есть
                options_line = re.sub(r'^(варианты|options):\s*', '', line, flags=re.IGNORECASE).strip()

                # Извлекаем варианты из строки
                if options_line.startswith('[') and options_line.endswith(']'):
                    options_str = options_line[1:-1]
                    options = [opt.strip() for opt in options_str.split(',')]
                else:
                    # Пытаемся извлечь варианты как элементы списка
                    options = re.findall(r'[\-\*]?\s*([^,\n]+)', options_line)
                    # Очищаем каждый вариант
                    options = [opt.strip().strip('*').strip('-').strip() for opt in options]

        # Если не нашли предложение в метке, используем первую значимую строку
        if not sentence:
            for line in cleaned_content.split('\n'):
                line = line.strip()
                if line and "..." in line:
                    sentence = line
                    break

        # Если не нашли варианты в метке, ищем в следующих строках после предложения
        if not options:
            lines = cleaned_content.split('\n')
            for i, line in enumerate(lines):
                if sentence and line.strip() == sentence:
                    # Берем следующие 4 строки как варианты
                    options = []
                    for j in range(i + 1, min(i + 5, len(lines))):
                        opt_line = lines[j].strip()
                        if opt_line:
                            # Удаляем маркеры списка и номера
                            clean_opt = re.sub(r'^[\-\*]?\s*\d?\.?\s*', '', opt_line)
                            options.append(clean_opt.strip())
                    if len(options) >= 4:
                        options = options[:4]
                    break

        # Проверяем наличие всех необходимых элементов
        if not sentence:
            logger.warning(f"Не найдено предложение в ответе: {content}")
            return None

        if not options or len(options) < 4:
            logger.warning(f"Недостаточно вариантов в ответе: {content}")
            return None

        # Удаляем лишние пробелы и кавычки
        sentence = sentence.strip().strip('"').strip("'")
        options = [opt.strip().strip('"').strip("'") for opt in options[:4]]

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


async def process_user_report(user_id, words, db_pool, session):
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
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                report_id = await conn.fetchval(
                    "INSERT INTO weekly_reports (user_id) VALUES ($1) RETURNING report_id",
                    user_id
                )

                for item in report_data:
                    await conn.execute(
                        "INSERT INTO report_words (report_id, word, sentence, options, correct_index) "
                        "VALUES ($1, $2, $3, $4, $5)",
                        report_id,
                        item["word"],
                        item["sentence"],
                        item["options"],
                        item["correct_index"]
                    )

    logger.info(f"Generated report for user {user_id} with {len(report_data)} words")
    return len(report_data)


async def generate_weekly_reports(db_pool, session):
    """Генерирует недельные отчеты с ограничением скорости"""
    user_words = await get_weekly_words_by_user(db_pool)
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
        words_processed = await process_user_report(user_id, selected_words, db_pool, session)

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


async def send_pending_reports(db_pool, session):
    """Отправляет все непотправленные отчеты"""
    reports = await db_pool.fetch(
        "SELECT report_id, user_id FROM weekly_reports WHERE sent = FALSE"
    )

    if not reports:
        logger.info("No pending reports")
        return

    tasks = []
    for report in reports:
        tasks.append(
            process_report_delivery(db_pool, session, report["report_id"], report["user_id"])
        )

    results = await asyncio.gather(*tasks)
    success_count = sum(1 for r in results if r)
    logger.info(f"Sent {success_count}/{len(reports)} reports")


async def process_report_delivery(db_pool, session, report_id, user_id):
    """Обрабатывает доставку одного отчета"""
    success = await send_user_report(db_pool, session, user_id, report_id)
    if success:
        await db_pool.execute(
            "UPDATE weekly_reports SET sent = TRUE WHERE report_id = $1",
            report_id
        )
    return success


async def cleanup_old_reports(db_pool, days: int = 30):
    """Очищает старые отчеты и связанные с ними данные"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Starting cleanup for reports older than {cutoff_date}")

        async with db_pool.acquire() as conn:
            old_reports = await conn.fetch(
                "SELECT report_id FROM weekly_reports WHERE generation_date < $1",
                cutoff_date
            )

            if not old_reports:
                logger.info("No old reports found for cleanup")
                return 0

            report_ids = [r["report_id"] for r in old_reports]
            logger.info(f"Found {len(report_ids)} old reports to delete")

            words_deleted = await conn.execute(
                "DELETE FROM report_words WHERE report_id = ANY($1::int[])",
                report_ids
            )

            reports_deleted = await conn.execute(
                "DELETE FROM weekly_reports WHERE report_id = ANY($1::int[])",
                report_ids
            )

            logger.info(
                f"Cleaned up {reports_deleted} reports and "
                f"{words_deleted} words older than {days} days"
            )
            return reports_deleted

    except Exception as e:
        logger.error(f"Error cleaning old reports: {e}")
        return False


async def main():
    """Основная асинхронная точка входа"""
    db_pool, session = await init_global_resources()

    # Проверка и логирование конфигурации API
    if AI_API_URL is None:
        logger.warning(f"AI_API_URL is None, using default: {DEFAULT_DEEPSEEK_URL}")
    else:
        logger.info(f"Using DeepSeek API at: {AI_API_URL}")

    try:
        if '--generate' in sys.argv:
            logger.info("Generating weekly reports with DeepSeek...")
            await generate_weekly_reports(db_pool, session)
        elif '--cleanup' in sys.argv:
            logger.info("Cleaning up old reports...")
            await cleanup_old_reports(db_pool, days=14)
        else:
            logger.info("Sending pending reports...")
            await send_pending_reports(db_pool, session)
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
    finally:
        await close_global_resources()


if __name__ == "__main__":
    asyncio.run(main())