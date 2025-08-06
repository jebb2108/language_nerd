import sys
import asyncio
import random
import aiohttp
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from routers.commands.weekly_message_commands import send_user_report
from config import (
    AI_API_KEY,
    AI_API_URL,
    init_global_resources,
    close_global_resources,
    logger
)

# Глобальный семафор для ограничения одновременных запросов
REQUEST_SEMAPHORE = asyncio.Semaphore(5)  # Максимум 5 одновременных запросов


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


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(aiohttp.ClientResponseError),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying ({retry_state.attempt_number}/5) for '{retry_state.args[0]}' "
        f"after {retry_state.outcome.exception().status} error"
    ) if retry_state.outcome and hasattr(retry_state.outcome.exception(), 'status') else None
)
async def generate_question_for_word(word, session):
    """Генерирует вопрос с вариантами ответов для слова с повторными попытками"""
    # Преобразуем слово в строку и очищаем
    word_str = str(word).strip()
    if not word_str:
        return None

    # Экранируем кавычки в слове
    safe_word = word_str.replace("'", "\\'").replace('"', '\\"')
    prompt = (
        f"Дай пример предложения, где нужно подобрать верное слово '{safe_word}', "
        "чтобы оценить знание ученика. На месте этого слова должно быть троеточие. "
        "В ответе должно быть одно верное и три неверных варианта в рандомном порядке "
        "с похожим значением. Строго следуй формату: предложение, ответы "
        "(через запятую на следующей строке в квадратных скобках)"
    )

    async with REQUEST_SEMAPHORE:  # Ограничиваем одновременные запросы
        try:
            # Убедимся, что AI_API_URL - строка
            if not isinstance(AI_API_URL, str):
                logger.error(f"AI_API_URL is not a string! Type: {type(AI_API_URL)}, Value: {AI_API_URL}")
                return None

            api_url = str(AI_API_URL).strip()

            async with session.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {AI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 150
                    },
                    timeout=60  # Увеличили таймаут
            ) as response:
                response.raise_for_status()
                data = await response.json()
                content = data['choices'][0]['message']['content'].strip()
                return parse_ai_response(content, safe_word)
        except aiohttp.ClientResponseError as e:
            # Для ошибки 429 добавляем дополнительную информацию
            if e.status == 429:
                logger.error(f"Rate limit exceeded for '{safe_word}'. Headers: {e.headers}")
            raise  # Повторная попытка будет обработана декоратором retry
        except Exception as e:
            logger.error(f"Non-retryable AI error for '{safe_word}': {e}", exc_info=True)
            return None


def parse_ai_response(content, original_word):
    """Парсит ответ от AI в нужный формат"""
    try:
        # Разделяем предложение и варианты ответов
        lines = content.strip().split('\n')
        sentence = lines[0].strip()

        # Извлекаем варианты ответов из квадратных скобок
        options_line = lines[1].strip() if len(lines) > 1 else ""
        if options_line.startswith('[') and options_line.endswith(']'):
            options = [opt.strip() for opt in options_line[1:-1].split(',')]
        else:
            # Альтернативный парсинг, если формат не идеальный
            if '[' in content and ']' in content:
                start_idx = content.index('[') + 1
                end_idx = content.index(']')
                options = [opt.strip() for opt in content[start_idx:end_idx].split(',')]
            else:
                return None

        # Проверяем наличие оригинального слова в вариантах
        if original_word not in options:
            logger.warning(f"Original word '{original_word}' not found in options: {options}")
            return None

        return {"sentence": sentence, "options": options}
    except Exception as e:
        logger.error(f"Parse error for '{original_word}': {e}", exc_info=True)
        return None


async def process_user_report(user_id, words, db_pool, session):
    """Обрабатывает отчет для одного пользователя"""
    report_data = []

    for word in words:
        # Преобразуем слово в строку и проверяем
        word_str = str(word).strip()
        if not word_str:
            continue

        # Генерируем вопрос для слова
        question_data = await generate_question_for_word(word_str, session)
        if not question_data:
            continue

        # Форматируем данные для сохранения
        try:
            # Находим индекс правильного ответа
            correct_index = question_data["options"].index(word_str)
            report_data.append({
                "word": word_str,
                "sentence": question_data["sentence"],
                "options": question_data["options"],
                "correct_index": correct_index
            })
        except ValueError:
            logger.warning(f"Correct word '{word_str}' not found in options")

        # Случайная задержка для снижения нагрузки
        await asyncio.sleep(0.5 + random.random() * 1.0)

    # Сохраняем отчет в БД
    if report_data:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Создаем отчет
                report_id = await conn.fetchval(
                    "INSERT INTO weekly_reports (user_id) VALUES ($1) RETURNING report_id",
                    user_id
                )

                # Сохраняем слова
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

    # Ограничиваем количество слов на пользователя
    max_words_per_user = 7
    max_users_per_minute = 10  # Ограничиваем количество пользователей в минуту

    processed_users = 0
    start_time = datetime.now()

    for record in user_words:
        words = record["words"]
        user_id = record["user_id"]

        # Выбираем случайные слова (но не более max_words_per_user)
        selected_words = random.sample(words, min(len(words), max_words_per_user))
        await process_user_report(user_id, selected_words, db_pool, session)

        processed_users += 1

        # Контроль скорости: не более max_users_per_minute пользователей в минуту
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
    # Получаем непотправленные отчеты
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
            # Получаем список отчетов для удаления
            old_reports = await conn.fetch(
                "SELECT report_id FROM weekly_reports WHERE generation_date < $1",
                cutoff_date
            )

            if not old_reports:
                logger.info("No old reports found for cleanup")
                return 0

            report_ids = [r["report_id"] for r in old_reports]
            logger.info(f"Found {len(report_ids)} old reports to delete")

            # Удаляем связанные слова отчетов
            words_deleted = await conn.execute(
                "DELETE FROM report_words WHERE report_id = ANY($1::int[])",
                report_ids
            )

            # Удаляем сами отчеты
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
    # Инициализация глобальных ресурсов
    db_pool, session = await init_global_resources()

    # Проверяем URL перед выполнением
    logger.info(f"AI_API_URL type: {type(AI_API_URL)}, value: {AI_API_URL}")

    try:
        if '--generate' in sys.argv:
            logger.info("Generating weekly reports with rate limiting...")
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