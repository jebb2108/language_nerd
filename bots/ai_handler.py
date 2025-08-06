import sys
import asyncio
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv(""".env""")

from routers.commands.weekly_message_commands import send_user_report
from config import (
    AI_API_KEY,
    AI_API_URL,
    init_global_resources,
    close_global_resources,
    logger
)

async def get_weekly_words_by_user(db_pool):
    """Получает слова за неделю, сгруппированные по пользователям"""
    query = """
        SELECT user_id, ARRAY_AGG(DISTINCT word) as words
        FROM words
        WHERE created_at <= $1
        GROUP BY user_id
        HAVING COUNT(word) > 1
    """
    week_ago = datetime.now() - timedelta(days=7)
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, week_ago)

async def generate_question_for_word(word, session):
    """Генерирует вопрос с вариантами ответов для слова"""
    prompt = (
        f"Дай пример предложения, где нужно подобрать верное слово '{word}', "
        "чтобы оценить знание ученика. На месте этого слова должно быть троеточие. "
        "В ответе должно быть одно верное и три неверных варианта в рандомном порядке "
        "с похожим значением. Строго следуй формату: предложение, ответы "
        "(через запятую на следующей строке в квадратных скобках)"
    )

    try:
        async with session.post(
                AI_API_URL,
                headers={"Authorization": f"Bearer {AI_API_KEY}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 150
                },
                timeout=30
        ) as response:
            response.raise_for_status()
            data = await response.json()
            content = data['choices'][0]['message']['content'].strip()
            return parse_ai_response(content)
    except Exception as e:
        logger.error(f"AI error for '{word}': {e}")
        return None


def parse_ai_response(content):
    """Парсит ответ от AI в нужный формат"""
    try:
        # Разделяем предложение и варианты ответов
        lines = content.strip().split('\n')
        sentence = lines[0].strip()

        # Извлекаем варианты ответов из квадратных скобок
        options_line = lines[1].strip() if len(lines) > 1 else ""
        if options_line.startswith('[') and options_line.endswith(']'):
            options = [opt.strip() for opt in options_line[1:-1].split(',')]
            return {"sentence": sentence, "options": options}

        # Альтернативный парсинг, если формат не идеальный
        if '[' in content and ']' in content:
            start_idx = content.index('[') + 1
            end_idx = content.index(']')
            options = [opt.strip() for opt in content[start_idx:end_idx].split(',')]
            return {"sentence": sentence, "options": options}

        return None
    except Exception:
        return None


async def process_user_report(user_id, words, db_pool, session):
    """Обрабатывает отчет для одного пользователя"""
    report_data = []

    for word in words:
        # Генерируем вопрос для слова
        question_data = await generate_question_for_word(word, session)
        if not question_data:
            continue

        # Форматируем данные для сохранения
        report_data.append({
            "word": word,
            "sentence": question_data["sentence"],
            "options": question_data["options"],
            "correct_index": question_data["options"].index(word)
        })
        await asyncio.sleep(0.5)  # Защита от rate limits

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
    """Генерирует недельные отчеты"""
    user_words = await get_weekly_words_by_user(db_pool)
    if not user_words:
        logger.info("No users with enough words")
        return

    # Ограничиваем количество слов на пользователя
    max_words_per_user = 7

    tasks = []
    for record in user_words:
        words = record["words"]
        user_id = record["user_id"]

        # Выбираем случайные слова (но не более max_words_per_user)
        selected_words = random.sample(words, min(len(words), max_words_per_user))
        tasks.append(process_user_report(user_id, selected_words, db_pool, session))

    results = await asyncio.gather(*tasks)
    total_words = sum(results)
    logger.info(f"Generated reports with total {total_words} words")


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
    success = await send_user _report(db_pool, session, user_id, report_id)
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

    try:
        if '--generate' in sys.argv:
            logger.info("Generating weekly reports...")
            await generate_weekly_reports(db_pool, session)
        elif '--cleanup' in sys.argv:
            logger.info("Cleaning up old reports...")
            await cleanup_old_reports(db_pool, days=14)
        else:
            logger.info("Sending pending reports...")
            await send_pending_reports(db_pool, session)
    except Exception as e:
        logger.critical(f"Critical error: {e}")
    finally:
        await close_global_resources()


if __name__ == "__main__":
    asyncio.run(main())