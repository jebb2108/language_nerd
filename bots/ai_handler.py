import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta
from aiolimiter import AsyncLimiter
from routers.commands.weekly_message_commands import send_user_report
from config import (
    AI_API_KEY,
    AI_API_URL,
    init_global_resources,
    close_global_resources,
    logger
)

# Лимит бесплатного тарифа OpenAI: ~20 запросов в минуту
RATE_LIMITER = AsyncLimiter(max_rate=20, time_period=60)
# Один запрос за раз (TPS)
REQUEST_SEMAPHORE = asyncio.Semaphore(1)

async def get_weekly_words_by_user(db_pool):
    query = """
        SELECT user_id, ARRAY_AGG(DISTINCT word) as words
        FROM words
        WHERE created_at >= $1 AND word IS NOT NULL
        GROUP BY user_id
        HAVING COUNT(word) > 1
    """
    week_ago = datetime.now() - timedelta(days=7)
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, week_ago)

async def generate_questions_for_words(words, session):
    """
    Пакетная генерация вопросов для списка слов одним запросом.
    Возвращает dict: word -> {sentence, options}
    """
    # Формируем промпт с несколькими словами
    words_list = '\n'.join(f"- '{w}'" for w in words)
    prompt = (
        f"Для каждого слова из списка ниже сгенерируй пример предложения с пропуском слова и варианты ответов:\n"
        f"{words_list}\n"
        "Формат выхода (JSON): [ {'word': ..., 'sentence': ..., 'options': [...]}, ... ]"
    )

    async with RATE_LIMITER:
        async with REQUEST_SEMAPHORE:
            try:
                async with session.post(
                    AI_API_URL,
                    headers={
                        "Authorization": f"Bearer {AI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 500
                    },
                    timeout=60
                ) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", "1"))
                        logger.error(f"429 Rate limit, retry after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        resp.raise_for_status()
                    else:
                        resp.raise_for_status()
                    data = await resp.json()
                content = data['choices'][0]['message']['content']
                # Парсим JSON-ответ
                import json
                parsed = json.loads(content)
                return {item['word']: item for item in parsed}
            except Exception as e:
                logger.error(f"Batch generation error: {e}", exc_info=True)
                return {}

async def process_user_report(user_id, words, db_pool, session):
    # Ограничим 7 слов
    selected = words[:7]
    questions = await generate_questions_for_words(selected, session)
    report_data = []
    for w in selected:
        q = questions.get(w)
        if not q or w not in q.get('options', []):
            logger.warning(f"Skipping word '{w}' — нет корректного ответа")
            continue
        report_data.append({
            'word': w,
            'sentence': q['sentence'],
            'options': q['options'],
            'correct_index': q['options'].index(w)
        })
    if report_data:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                report_id = await conn.fetchval(
                    "INSERT INTO weekly_reports(user_id) VALUES($1) RETURNING report_id", user_id
                )
                for item in report_data:
                    await conn.execute(
                        "INSERT INTO report_words(report_id, word, sentence, options, correct_index) VALUES($1,$2,$3,$4,$5)",
                        report_id,
                        item['word'],
                        item['sentence'],
                        item['options'],
                        item['correct_index']
                    )
    logger.info(f"User {user_id}: {len(report_data)} words processed")
    return len(report_data)

async def send_pending_reports(db_pool, session):
    reports = await db_pool.fetch("SELECT report_id, user_id FROM weekly_reports WHERE sent=FALSE")
    if not reports:
        logger.info("No pending reports")
        return
    for rep in reports:
        ok = await send_user_report(db_pool, session, rep['user_id'], rep['report_id'])
        if ok:
            await db_pool.execute(
                "UPDATE weekly_reports SET sent=TRUE WHERE report_id=$1", rep['report_id']
            )
        await asyncio.sleep(3)  # чтобы не бить API

async def cleanup_old_reports(db_pool, days=30):
    cutoff = datetime.now() - timedelta(days=days)
    async with db_pool.acquire() as conn:
        old = await conn.fetch("SELECT report_id FROM weekly_reports WHERE generation_date < $1", cutoff)
        if not old:
            return 0
        ids = [r['report_id'] for r in old]
        await conn.execute("DELETE FROM report_words WHERE report_id = ANY($1::int[])", ids)
        deleted = await conn.execute("DELETE FROM weekly_reports WHERE report_id = ANY($1::int[])", ids)
        logger.info(f"Cleaned {deleted} old reports")
        return deleted

async def generate_weekly_reports(db_pool, session):
    users = await get_weekly_words_by_user(db_pool)
    for rec in users:
        await process_user_report(rec['user_id'], rec['words'], db_pool, session)
        await asyncio.sleep(5)

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
