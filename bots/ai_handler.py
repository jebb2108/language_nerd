import sys
import asyncio
import json
from datetime import datetime, timedelta

import openai
from aiolimiter import AsyncLimiter
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from openai import RateLimitError
from routers.commands.weekly_message_commands import send_user_report
from config import (
    AI_API_KEY,
    AI_API_URL,
    init_global_resources,
    close_global_resources,
    logger
)

# Настройка OpenAI SDK
openai.api_key = AI_API_KEY
openai.api_base = AI_API_URL

# Лимит бесплатного тарифа: до 15 запросов в минуту
RATE_LIMITER = AsyncLimiter(max_rate=15, time_period=60)
# Размер батча слов
BATCH_SIZE = 3
# Максимальное количество попыток при 429
MAX_RETRIES = 5

async def get_weekly_words_by_user(db_pool):
    query = """
        SELECT user_id, ARRAY_AGG(DISTINCT word) AS words
        FROM words
        WHERE created_at >= $1 AND word IS NOT NULL
        GROUP BY user_id
        HAVING COUNT(word) > 1
    """
    week_ago = datetime.now() - timedelta(days=7)
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, week_ago)

@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(MAX_RETRIES),
    reraise=True
)
async def generate_questions_for_words(words: list) -> dict:
    """
    Генерирует вопросы для списка слов (размер списка <= BATCH_SIZE).
    При RateLimitError автоматически выполняет ретрай с backoff.
    Возвращает словарь: слово -> {sentence, options}.
    """
    prompt_items = '\n'.join(f"- '{w}'" for w in words)
    system_prompt = (
        "Для каждого слова из списка ниже сгенерируй предложение с пропуском слова и варианты"
        " ответов. Формат (JSON): [{ 'word': ..., 'sentence': ..., 'options': [...] }, ...]"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_items}
    ]

    async with RATE_LIMITER:
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
        except RateLimitError as e:
            # пауза по Retry-After если указан
            headers = getattr(e, 'headers', {}) or {}
            retry_after = headers.get('Retry-After') or headers.get('retry-after')
            if retry_after:
                await asyncio.sleep(int(retry_after))
            logger.warning(f"Rate limit hit, retrying batch {words}")
            raise

    try:
        content = response.choices[0].message.content
        parsed = json.loads(content)
        return {item['word']: item for item in parsed}
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}\nContent: {content}")
        return {}

async def process_user_report(user_id: int, words: list, db_pool, session=None):
    """Обрабатывает одного пользователя: генерирует вопросы и сохраняет отчет"""
    selected = words[:7]
    report_data = []

    # разбиваем на батчи по BATCH_SIZE
    for i in range(0, len(selected), BATCH_SIZE):
        batch = selected[i:i + BATCH_SIZE]
        try:
            questions = await generate_questions_for_words(batch)
        except RateLimitError:
            logger.error(f"Skipping batch {batch} after max retries")
            continue

        for w in batch:
            q = questions.get(w)
            if not q or w not in q.get('options', []):
                logger.warning(f"Skipping '{w}' — нет корректного ответа")
                continue
            report_data.append({
                'word': w,
                'sentence': q['sentence'],
                'options': q['options'],
                'correct_index': q['options'].index(w)
            })

        # небольшая задержка, чтобы не перегрузить лимитер
        await asyncio.sleep(1)

    # сохраняем отчет
    if report_data:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                report_id = await conn.fetchval(
                    "INSERT INTO weekly_reports(user_id) VALUES($1) RETURNING report_id", user_id
                )
                for item in report_data:
                    await conn.execute(
                        "INSERT INTO report_words(report_id, word, sentence, options, correct_index)"
                        " VALUES($1,$2,$3,$4,$5)",
                        report_id,
                        item['word'],
                        item['sentence'],
                        item['options'],
                        item['correct_index']
                    )
    logger.info(f"User {user_id}: processed {len(report_data)} words")
    return len(report_data)

async def send_pending_reports(db_pool, session=None):
    """Отправляет отчеты и помечает их как отправленные"""
    reports = await db_pool.fetch(
        "SELECT report_id, user_id FROM weekly_reports WHERE sent = FALSE"
    )
    for rep in reports:
        ok = await send_user_report(db_pool, session, rep['user_id'], rep['report_id'])
        if ok:
            await db_pool.execute(
                "UPDATE weekly_reports SET sent = TRUE WHERE report_id = $1", rep['report_id']
            )
        await asyncio.sleep(1)

async def cleanup_old_reports(db_pool, days: int = 30):
    cutoff = datetime.now() - timedelta(days=days)
    async with db_pool.acquire() as conn:
        old = await conn.fetch(
            "SELECT report_id FROM weekly_reports WHERE generation_date < $1", cutoff
        )
        if not old:
            return 0
        ids = [r['report_id'] for r in old]
        await conn.execute(
            "DELETE FROM report_words WHERE report_id = ANY($1::int[])", ids
        )
        deleted = await conn.execute(
            "DELETE FROM weekly_reports WHERE report_id = ANY($1::int[])", ids
        )
        logger.info(f"Cleaned up {deleted} old reports")
        return deleted

async def generate_weekly_reports(db_pool, session=None):
    users = await get_weekly_words_by_user(db_pool)
    for rec in users:
        await process_user_report(rec['user_id'], rec['words'], db_pool)
        await asyncio.sleep(2)

async def main():
    db_pool, session = await init_global_resources()
    try:
        if '--generate' in sys.argv:
            await generate_weekly_reports(db_pool, session)
        elif '--cleanup' in sys.argv:
            await cleanup_old_reports(db_pool, days=14)
        else:
            await send_pending_reports(db_pool, session)
    finally:
        await close_global_resources()

if __name__ == '__main__':
    asyncio.run(main())
