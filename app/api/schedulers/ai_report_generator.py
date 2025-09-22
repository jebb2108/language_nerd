import logging
import asyncio
import random
import sys

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

from app.api.schedulers.ai_cleanup import cleanup_old_reports
from app.dependencies import get_db
from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='schedulers')

AI_LAST_REQUEST_TIME = config.AI_LAST_REQUEST_TIME

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
async def generate_question_for_word(word):
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

    async with config.REQUEST_SEMAPHORE:
        async with config.REQUEST_RATE_LIMITER:
            current_time = time.time()
            if current_time - AI_LAST_REQUEST_TIME < 1.2:
                wait_time = 1.2 - (current_time - AI_LAST_REQUEST_TIME)
                await asyncio.sleep(wait_time)

            try:
                # Обработка случая, когда AI_API_URL не задан
                if config.AI_API_URL is None:
                    logger.warning("AI_API_URL is None, using default DeepSeek URL")
                    api_url = config.DEFAULT_DEEPSEEK_URL
                elif not isinstance(config.AI_API_URL, str):
                    logger.warning(f"AI_API_URL is not a string! Type: {type(config.AI_API_URL)}, Value: {config.AI_API_URL}")
                    api_url = config.DEFAULT_DEEPSEEK_URL
                else:
                    api_url = config.AI_API_URL.strip()
                async with aiohttp.ClientSession as session:
                    # Формируем запрос для DeepSeek API
                    async with session.post(
                            api_url,
                            headers={
                                "Authorization": f"Bearer {config.AI_API_KEY}",
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


async def process_user_report(user_id: int, words: List[str], db) -> int:
    """Обрабатывает отчет для одного пользователя"""

    report_data = []

    for word in words:
        word_str = str(word).strip()
        if not word_str:
            continue

        try:
            question_data = await generate_question_for_word(word_str)
        except Exception as e:
            logger.error(f"Failed to generate question for '{word_str}': {e}")
            question_data = None

        if not question_data:
            continue

        options = question_data["options"].copy()
        random.shuffle(options)

        try:
            # Поиск правильного ответа без учета регистра
            correct_index = next(i for i, opt in enumerate(options) if opt.lower() == word_str.lower())

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
        report_id = await db.create_report(user_id)
        await db.add_words_to_report(report_id, report_data)

    logger.info(f"Generated report for user {user_id} with {len(report_data)} words")
    return len(report_data)


async def generate_weekly_reports():
    """Генерирует недельные отчеты с ограничением скорости"""
    db = await get_db()
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
        words_processed = await process_user_report(user_id, selected_words, db)

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


async def generate_weekly_reports():
    """Генерирует недельные отчеты с ограничением скорости"""

    db = await get_db()
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
        words_processed = await process_user_report(user_id, selected_words, db)

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


if __name__ == '__main__':
    asyncio.run(generate_weekly_reports())