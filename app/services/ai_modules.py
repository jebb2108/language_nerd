import logging
import asyncio
import random
import re
import time
import aiohttp
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from aiogram.exceptions import (
    TelegramRetryAfter,
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramServerError,
    TelegramAPIError
)

from app.models import UserWords, ReportData

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

from app.models import DeliveryResult, UserReport, PendingReport
from config import LOG_CONFIG, config


if TYPE_CHECKING:
    from aiogram import Bot
    from app.services.database import DatabaseService

# Настройка логирования
logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="ai_modules")

# ========== ERROR HANDLING ==========
class APIErrorHandler:
    """Обработчик ошибок API"""

    @staticmethod
    def should_retry(result: Any) -> bool:
        """Определяет, нужно ли повторять запрос при ошибке API"""
        return result is None

    @staticmethod
    def is_payment_required_error(exception: Exception) -> bool:
        """Проверяет, является ли ошибка Payment Required (402)"""
        return (
            isinstance(exception, aiohttp.ClientResponseError)
            and exception.status == 402
        )

    @staticmethod
    def is_rate_limit_error(exception: Exception) -> bool:
        """Проверяет, является ли ошибка Rate Limit (429)"""
        return (
            isinstance(exception, aiohttp.ClientResponseError)
            and exception.status == 429
        )


class ResponseParser:
    """Парсер ответов от DeepSeek API"""

    @staticmethod
    def parse_deepseek_response(
        content: str, original_word: str
    ) -> Optional[Dict[str, Any]]:
        """Парсит ответ от DeepSeek в нужный формат"""
        try:
            cleaned_content = ResponseParser._clean_content(content)
            lines = ResponseParser._split_and_clean_lines(cleaned_content)

            sentence = ResponseParser._extract_sentence(lines)
            options = ResponseParser._extract_options(lines)

            if not ResponseParser._validate_response(sentence, options, original_word):
                return None

            return {"sentence": sentence, "options": options[:4]}

        except Exception as e:
            logger.error(f"Parse error for '{original_word}': {e}", exc_info=True)
            return None

    @staticmethod
    def _clean_content(content: str) -> str:
        """Очищает контент от лишнего форматирования"""
        return re.sub(r"\*|\[.*?\]|\(.*?\)", "", content)

    @staticmethod
    def _split_and_clean_lines(content: str) -> List[str]:
        """Разбивает контент на строки и очищает их"""
        return [line.strip() for line in content.split("\n") if line.strip()]

    @staticmethod
    def _extract_sentence(lines: List[str]) -> Optional[str]:
        """Извлекает предложение из строк ответа"""
        for line in lines:
            if "..." in line:
                sentence = (
                    re.sub(
                        r"^(предложение|sentence):\s*", "", line, flags=re.IGNORECASE
                    )
                    .strip()
                    .strip('"')
                    .strip("'")
                )
                return sentence

        return lines[0] if lines else None

    @staticmethod
    def _extract_options(lines: List[str]) -> List[str]:
        """Извлекает варианты ответов из строк"""
        options = []

        for i, line in enumerate(lines):
            if re.match(r"^(варианты|options):", line, re.IGNORECASE):
                options = ResponseParser._parse_options_from_line(line, lines, i)
                break

        # Если не нашли через метку, ищем список элементов
        if not options:
            options = ResponseParser._find_options_without_label(lines)

        return options

    @staticmethod
    def _parse_options_from_line(
        current_line: str, lines: List[str], current_index: int
    ) -> List[str]:
        """Парсит варианты из текущей строки и следующих строк"""
        options = []

        # Варианты в одной строке через запятую
        after_colon = re.sub(
            r"^(варианты|options):\s*", "", current_line, flags=re.IGNORECASE
        )
        if after_colon:
            inline_options = [
                opt.strip() for opt in after_colon.split(",") if opt.strip()
            ]
            options.extend(inline_options)

        # Варианты в следующих строках
        for j in range(current_index + 1, min(current_index + 6, len(lines))):
            clean_option = ResponseParser._clean_option_line(lines[j])
            if clean_option:
                options.append(clean_option)

        return options

    @staticmethod
    def _clean_option_line(line: str) -> str:
        """Очищает строку с вариантом ответа"""
        return re.sub(r"^[-\*]?\s*\d?\.?\s*", "", line).strip()

    @staticmethod
    def _find_options_without_label(lines: List[str]) -> List[str]:
        """Ищет варианты без явной метки 'Варианты:'"""
        candidate_options = []
        for line in lines:
            clean_option = ResponseParser._clean_option_line(line)
            if clean_option and "..." not in line:
                candidate_options.append(clean_option)

        return candidate_options if len(candidate_options) >= 4 else []

    @staticmethod
    def _validate_response(
        sentence: Optional[str], options: List[str], original_word: str
    ) -> bool:
        """Валидирует ответ от API"""
        if not sentence:
            logger.warning(
                f"Не найдено предложение в ответе для слова '{original_word}'"
            )
            return False

        if len(options) < 4:
            logger.warning(
                f"Недостаточно вариантов в ответе (найдено {len(options)}) для слова '{original_word}'"
            )
            return False

        if original_word.lower() not in [opt.lower() for opt in options]:
            logger.warning(
                f"Original word '{original_word}' not found in options: {options}"
            )
            return False

        return True


# ========== API CLIENT ==========
class DeepSeekClient:
    """Клиент для работы с DeepSeek API"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.request_delay = 1.2
        self.last_request_time = 0

    async def _ensure_rate_limit(self):
        """Обеспечивает соблюдение rate limit"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            wait_time = self.request_delay - time_since_last_request
            await asyncio.sleep(wait_time)


    async def _make_api_request(
        self, session: aiohttp.ClientSession, url: str, data: Dict[str, Any]
    ) -> None:

        """Выполняет запрос к API"""
        async with session.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=data,
            timeout=60,
            verify_ssl=config.VERIFY_SSL,  # Для разработки

        ) as response:

            self.last_request_time = time.time()

            if response.status == 429:
                await self._handle_rate_limit(response)
            elif response.status == 402:
                return self._handle_payment_required()

            response.raise_for_status()
            return await response.json()


    async def generate_question(self, word: str) -> Optional[Dict[str, Any]]:
        """Генерирует вопрос для слова через API"""
        word_str = str(word).strip()
        if not word_str:
            return None

        await self._ensure_rate_limit()

        api_url = self._get_api_url()
        prompt = self._build_prompt(word_str)
        request_data = self._build_request_data(prompt)

        async with aiohttp.ClientSession() as session:
            data = await self._make_api_request(session, api_url, request_data)

            if data is None:  # Обработка случая с 402 ошибкой
                return None

            content = data["choices"][0]["message"]["content"].strip()
            return ResponseParser.parse_deepseek_response(content, word_str)


    @staticmethod
    def _build_prompt(word: str) -> str:
        """Строит промпт для генерации вопроса"""
        safe_word = word.replace("'", "\\'").replace('"', '\\"')

        return (
            f"Создай вопрос для проверки знания слова '{safe_word}'. "
            "Придумай предложение, где вместо этого слова стоит троеточие. "
            "Предоставь один правильный вариант ответа и три неправильных, "
            "но похожих по значению. Варианты должны быть в случайном порядке.\n\n"
            "Формат ответа:\n"
            "Предложение: [предложение с ...]\n"
            "Варианты: [правильный, неправильный1, неправильный2, неправильный3]\n\n"
            "ВАЖНО: Не добавляй дополнительные пояснения, комментарии или разметку!"
        )

    @staticmethod
    def _build_request_data(prompt: str) -> Dict[str, Any]:
        """Строит данные для запроса"""
        return {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты полезный помощник для изучения английского языка. Отвечай строго в указанном формате без дополнительных пояснений.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stop": None,
        }

    @staticmethod
    async def _handle_rate_limit(response: aiohttp.ClientResponse) -> None:
        """Обрабатывает rate limit (429)"""
        retry_after = response.headers.get("Retry-After", "5")
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
            message="Too Many Requests",
            headers=response.headers,
        )

    @staticmethod
    def _handle_payment_required() -> None:
        """Обрабатывает ошибку оплаты (402)"""
        logger.critical("DeepSeek API requires payment. Please upgrade your account.")
        return None

    @staticmethod
    def _get_api_url() -> str:
        """Получает URL для API запроса"""
        if config.AI_API_URL is None:
            logger.warning("AI_API_URL is None, using default DeepSeek URL")
            return config.DEFAULT_DEEPSEEK_URL
        elif not isinstance(config.AI_API_URL, str):
            logger.warning(
                f"AI_API_URL is not a string! Type: {type(config.AI_API_URL)}"
            )
            return config.DEFAULT_DEEPSEEK_URL
        else:
            return config.AI_API_URL.strip()


# ========== QUESTION GENERATOR ==========
class QuestionGenerator:
    """Генератор вопросов для слов"""

    def __init__(self, api_client: DeepSeekClient):
        self.api_client = api_client

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=10, max=120),
        retry=(
            retry_if_exception_type(aiohttp.ClientResponseError)
            & retry_if_result(
                lambda e: not APIErrorHandler.is_payment_required_error(e)
            )
        )
        | retry_if_result(APIErrorHandler.should_retry),
        reraise=True,
    )
    async def generate_question_for_word(self, word: str) -> Optional[Dict[str, Any]]:
        """Генерирует вопрос с вариантами ответов для слова"""
        word_str = str(word).strip()
        if not word_str:
            logger.warning("Empty word provided")
            return None

        try:
            async with config.REQUEST_SEMAPHORE:
                async with config.REQUEST_RATE_LIMITER:
                    return await self.api_client.generate_question(word_str)

        except aiohttp.ClientResponseError as e:
            if e.status == 402:
                logger.critical(
                    "DeepSeek API requires payment. Please upgrade your account."
                )
                return None
            elif e.status == 429:
                logger.error(
                    f"Rate limit exceeded for '{word_str}'. Headers: {e.headers}"
                )
            raise
        except Exception as e:
            logger.error(f"DeepSeek API error for '{word_str}': {e}", exc_info=True)
            return None


# ========== REPORT PROCESSOR ==========
class ReportProcessor:
    """Обработчик отчетов пользователей"""

    def __init__(
        self, q_gen: QuestionGenerator, max_words_per_user: int = 5
    ):
        self.question_generator = q_gen
        self.max_words_per_user = max_words_per_user

    async def process_single_word(self, word: str) -> Optional[ReportData]:
        """Обрабатывает одно слово и возвращает данные для отчета"""
        word_str = str(word).strip()
        if not word_str:
            return None

        try:
            question_data = await self.question_generator.generate_question_for_word(
                word_str
            )
        except Exception as e:
            logger.error(f"Failed to generate question for '{word_str}': {e}")
            return None

        if not question_data:
            return None

        # Перемешиваем варианты и находим правильный ответ
        options = question_data["options"].copy()
        random.shuffle(options)

        try:
            correct_index = next(
                i for i, opt in enumerate(options) if opt.lower() == word_str.lower()
            )

            return ReportData(
                word=word_str,
                sentence=question_data["sentence"],
                options=options,
                correct_index=correct_index,
            )

        except (StopIteration, ValueError):
            logger.warning(
                f"Correct word '{word_str}' not found in options: {question_data['options']}"
            )
            return None

    async def process_user_words(self, user_id: int, words: List[str], db) -> int:
        """Обрабатывает слова пользователя и сохраняет отчет"""
        selected_words = random.sample(words, min(len(words), self.max_words_per_user))

        report_data = []
        for word in selected_words:
            word_data = await self.process_single_word(word)
            if word_data:
                report_data.append(
                    {
                        "word": word_data.word,
                        "sentence": word_data.sentence,
                        "options": word_data.options,
                        "correct_index": word_data.correct_index,
                    }
                )

        # Сохраняем отчет в БД
        if report_data:
            report_id = await db.create_report(user_id)
            await db.add_words_to_report(report_id, report_data)
            logger.info(
                f"Generated report for user {user_id} with {len(report_data)} words"
            )
        else:
            logger.warning(f"No questions generated for user {user_id}")

        return len(report_data)


# ========== SCHEDULER ==========
class WeeklyReportScheduler:
    """Планировщик недельных отчетов"""

    def __init__(
        self, report_prc: ReportProcessor, max_users_per_minute: int = 3
    ):
        self.report_processor = report_prc
        self.max_users_per_minute = max_users_per_minute


    async def process_single_user(self, user_record: UserWords, db) -> bool:
        """Обрабатывает одного пользователя"""
        user_id = user_record.user_id

        if await self.should_skip_user(user_id, db):
            logger.info(f"Skipping generation for blocked user {user_id}")
            return False

        words_processed = await self.report_processor.process_user_words(
            user_id, user_record.words, db
        )

        if words_processed == 0:
            logger.warning(f"Skipping user {user_id} - no questions generated")
            return False

        return True

    async def generate_weekly_reports(self) -> None:
        """Генерирует недельные отчеты с ограничением скорости"""
        from app.dependencies import get_db

        db = await get_db()
        user_words_records = await db.get_weekly_words_by_user()

        if not user_words_records:
            logger.info("No users with enough words")
            return

        # Преобразуем записи в объекты UserWords
        user_words = [
            UserWords(user_id=record["user_id"], words=record["words"])
            for record in user_words_records
        ]

        processed_users = 0
        start_time = datetime.now()

        for user_record in user_words:
            success = await self.process_single_user(user_record, db)
            if success:
                processed_users += 1

            # Контроль скорости обработки
            elapsed = (datetime.now() - start_time).total_seconds()
            required_delay = max(0, (60 / self.max_users_per_minute) - elapsed)

            if required_delay > 0:
                logger.info(
                    f"Rate limiting: waiting {required_delay:.1f}s before next user"
                )
                await asyncio.sleep(required_delay)
                start_time = datetime.now()
            else:
                start_time = datetime.now()

        logger.info(f"Generated reports for {processed_users} users")

    @staticmethod
    async def should_skip_user(user_id: int, db) -> bool:
        """Проверяет, нужно ли пропустить пользователя"""
        return await db.is_user_blocked(user_id)



# ========== RATE LIMITER ==========
class TelegramRateLimiter:
    """Обработчик ограничений скорости Telegram API"""

    def __init__(self):
        self.retry_until_time = config.TELEGRAM_RETRY_UNTIL_TIME
        self.last_request_time = config.AI_LAST_REQUEST_TIME
        self.semaphore = config.TELEGRAM_API_SEMAPHORE
        self.min_delay = config.TELEGRAM_MIN_DELAY_BETWEEN_REQUESTS

    async def wait_for_rate_limit(self) -> None:
        """Ожидает выполнения условий rate limiting"""
        async with self.semaphore:
            await self._wait_for_proactive_limit()
            await self._wait_for_reactive_limit()
            self.last_request_time = time.time()

    async def _wait_for_proactive_limit(self) -> None:
        """Проактивное ограничение скорости"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_delay:
            wait_time = self.min_delay - time_since_last_request
            logger.debug(f"Проактивное ограничение скорости: ожидание {wait_time:.3f}с")
            await asyncio.sleep(wait_time)

    async def _wait_for_reactive_limit(self) -> None:
        """Реактивное ограничение скорости (глобальное)"""
        if time.time() < self.retry_until_time:
            sleep_duration = self.retry_until_time - time.time()
            logger.warning(f"Глобальное ожидание флуда Telegram API: пауза на {sleep_duration:.2f}с")
            await asyncio.sleep(sleep_duration)

    def set_global_retry_after(self, retry_after: float) -> None:
        """Устанавливает глобальную задержку после получения 429"""
        self.retry_until_time = time.time() + retry_after


# ========== ERROR HANDLER ==========
class TelegramErrorHandler:
    """Обработчик ошибок Telegram API"""

    @staticmethod
    async def handle_error(error: Exception, user_id: int, report_id: int, db) -> DeliveryResult:
        """Обрабатывает ошибку и возвращает результат"""
        if isinstance(error, TelegramRetryAfter):
            return await TelegramErrorHandler._handle_retry_after(error, user_id, report_id)
        elif isinstance(error, TelegramForbiddenError):
            return await TelegramErrorHandler._handle_forbidden_error(error, user_id, report_id, db)
        elif isinstance(error, TelegramBadRequest):
            return await TelegramErrorHandler._handle_bad_request(error, user_id, report_id, db)
        elif isinstance(error, (TelegramNetworkError, TelegramServerError)):
            return await TelegramErrorHandler._handle_temporary_error(error, user_id, report_id)
        elif isinstance(error, TelegramAPIError):
            return await TelegramErrorHandler._handle_api_error(error, user_id, report_id)
        else:
            return await TelegramErrorHandler._handle_unexpected_error(error, user_id, report_id)

    @staticmethod
    async def _handle_retry_after(error: TelegramRetryAfter, user_id: int, report_id: int) -> DeliveryResult:
        """Обрабатывает ошибку ограничения скорости"""
        logger.warning(
            f"Ожидание флуда Telegram API для пользователя {user_id}. "
            f"Повторная попытка через {error.retry_after} секунд."
        )
        return DeliveryResult(
            success=False,
            report_id=report_id,
            user_id=user_id,
            error_type="rate_limit",
            error_message=f"Retry after {error.retry_after} seconds"
        )

    @staticmethod
    async def _handle_forbidden_error(error: TelegramForbiddenError, user_id: int, report_id: int,
                                      db) -> DeliveryResult:
        """Обрабатывает ошибку блокировки бота"""
        logger.warning(
            f"Бот заблокирован пользователем {user_id} (отчет {report_id}): {error.message}"
        )
        await db.mark_user_as_blocked(user_id)
        await db.mark_report_as_sent(report_id, status="blocked")
        return DeliveryResult(
            success=False,
            report_id=report_id,
            user_id=user_id,
            error_type="forbidden",
            error_message=error.message
        )

    @staticmethod
    async def _handle_bad_request(error: TelegramBadRequest, user_id: int, report_id: int, db) -> DeliveryResult:
        """Обрабатывает ошибку некорректного запроса"""
        logger.error(
            f"Некорректный запрос Telegram для пользователя {user_id} (отчет {report_id}): {error.message}"
        )
        await db.mark_report_as_sent(report_id, status="bad_request_failed")
        return DeliveryResult(
            success=False,
            report_id=report_id,
            user_id=user_id,
            error_type="bad_request",
            error_message=error.message
        )

    @staticmethod
    async def _handle_temporary_error(error: Exception, user_id: int, report_id: int) -> DeliveryResult:
        """Обрабатывает временные ошибки сети/сервера"""
        logger.error(
            f"Временная ошибка Telegram API для пользователя {user_id} (отчет {report_id}): {error}"
        )
        return DeliveryResult(
            success=False,
            report_id=report_id,
            user_id=user_id,
            error_type="temporary",
            error_message=str(error)
        )

    @staticmethod
    async def _handle_api_error(error: TelegramAPIError, user_id: int, report_id: int) -> DeliveryResult:
        """Обрабатывает прочие ошибки API"""
        logger.error(
            f"Необработанная ошибка Telegram API для пользователя {user_id} (отчет {report_id}): {error}",
            exc_info=True
        )
        return DeliveryResult(
            success=False,
            report_id=report_id,
            user_id=user_id,
            error_type="api_error",
            error_message=str(error)
        )

    @staticmethod
    async def _handle_unexpected_error(error: Exception, user_id: int, report_id: int) -> DeliveryResult:
        """Обрабатывает неожиданные ошибки"""
        logger.critical(
            f"Неожиданная ошибка при доставке отчета для пользователя {user_id} (отчет {report_id}): {error}",
            exc_info=True
        )
        return DeliveryResult(
            success=False,
            report_id=report_id,
            user_id=user_id,
            error_type="unexpected",
            error_message=str(error)
        )


# ========== REPORT SENDER ==========
class ReportSender:
    """Отправитель отчетов пользователям"""

    def __init__(self, bot: "Bot", rate_limiter: TelegramRateLimiter):
        self.bot = bot
        self.rate_limiter = rate_limiter

    async def send_report_message(self, user_report: UserReport) -> bool:
        """Отправляет сообщение с отчетом пользователю"""

        from app.bots.main_bot.translations import WEEKLY_QUIZ
        from app.bots.main_bot.keyboards.inline_keyboards import begin_weekly_quiz_keyboard

        try:
            lang_code = user_report.user_info["lang_code"]

            await self.bot.send_message(
                chat_id=user_report.user_id,
                text=WEEKLY_QUIZ["weekly_report"].format(
                    total=len(user_report.words)
                ),
                reply_markup=begin_weekly_quiz_keyboard(lang_code, user_report.report_id),
            )

            return True

        except (TelegramForbiddenError, TelegramBadRequest):
            # Пробрасываем специфические ошибки для обработки на верхнем уровне
            logger.error(f"User {user_report.user_id} has blocked this bot")
            return False

        except Exception as e:
            logger.error(
                f"Ошибка при отправке отчета {user_report.report_id} "
                f"пользователю {user_report.user_id}: {e}",
                exc_info=True
            )
            return False


# ========== REPORT DELIVERY MANAGER ==========
class ReportDeliveryManager:
    """Менеджер доставки отчетов"""

    def __init__(self, tg_bot: "Bot", database: "DatabaseService", r_limiter: TelegramRateLimiter, ):
        self.bot = tg_bot
        self.db = database
        self.rate_limiter = r_limiter
        self.report_sender = ReportSender(tg_bot, r_limiter)
        self.error_handler = TelegramErrorHandler()

    async def process_single_report(self, pending_report: PendingReport) -> DeliveryResult:
        """Обрабатывает доставку одного отчета"""
        try:
            # Ожидаем выполнения условий rate limiting
            await self.rate_limiter.wait_for_rate_limit()

            # Получаем данные отчета
            user_report = await self._get_user_report_data(pending_report)
            if not user_report:
                return DeliveryResult(
                    success=False,
                    report_id=pending_report.report_id,
                    user_id=pending_report.user_id,
                    error_type="data_not_found",
                    error_message="Report data not found"
                )

            # Отправляем сообщение
            success = await self.report_sender.send_report_message(user_report)

            if success:
                await self.db.mark_report_as_sent(pending_report.report_id)
                logger.info(
                    f"Отчет {pending_report.report_id} успешно отправлен "
                    f"пользователю {pending_report.user_id}"
                )
                return DeliveryResult(
                    success=True,
                    report_id=pending_report.report_id,
                    user_id=pending_report.user_id
                )
            else:
                logger.error(
                    f"Не удалось отправить отчет {pending_report.report_id} "
                    f"пользователю {pending_report.user_id}"
                )
                return DeliveryResult(
                    success=False,
                    report_id=pending_report.report_id,
                    user_id=pending_report.user_id,
                    error_type="send_failed",
                    error_message="Send message returned False"
                )

        except Exception as e:
            # Обрабатываем ошибки через error handler
            result = await self.error_handler.handle_error(
                e, pending_report.user_id, pending_report.report_id, self.db
            )

            # Особый случай: обновляем глобальный rate limiter для RetryAfter
            if isinstance(e, TelegramRetryAfter):
                self.rate_limiter.set_global_retry_after(e.retry_after)

            return result

    async def _get_user_report_data(self, pending_report: PendingReport) -> Optional[UserReport]:
        """Получает данные отчета из базы данных"""
        try:
            report = await self.db.get_report(pending_report.report_id)
            words = await self.db.get_weekly_words(pending_report.report_id)
            user_info = await self.db.get_user_info(pending_report.user_id)

            if not report or not words:
                logger.warning(f"No report data found for report_id: {pending_report.report_id}")
                return None

            return UserReport(
                report_id=pending_report.report_id,
                user_id=pending_report.user_id,
                words=words,
                user_info=user_info
            )

        except Exception as e:
            logger.error(
                f"Ошибка при получении данных отчета {pending_report.report_id}: {e}",
                exc_info=True
            )
            return None


# ========== PENDING REPORTS PROCESSOR ==========
class PendingReportsProcessor:
    """Процессор ожидающих отчетов"""

    def __init__(self, del_manager: ReportDeliveryManager):
        self.delivery_manager = del_manager

    async def process_all_pending_reports(self) -> Dict[str, Any]:
        """Обрабатывает все ожидающие отчеты"""
        pending_reports = await self._get_pending_reports()
        if not pending_reports:
            logger.info("Нет ожидающих отчетов")
            return {"success_count": 0, "failed_count": 0, "failed_reports": []}

        logger.info(f"Попытка отправить {len(pending_reports)} ожидающих отчетов.")

        # Обрабатываем отчеты параллельно
        tasks = [
            self.delivery_manager.process_single_report(report)
            for report in pending_reports
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Анализируем результаты
        return self._analyze_results(results, pending_reports)

    async def _get_pending_reports(self) -> List[PendingReport]:
        """Получает список ожидающих отчетов"""
        reports_data = await self.delivery_manager.db.get_pending_reports()
        return [
            PendingReport(report_id=rec["report_id"], user_id=rec["user_id"])
            for rec in reports_data
        ]


    @staticmethod
    def _analyze_results(results: List[Any], pending_reports: List[PendingReport]) -> Dict[str, Any]:
        """Анализирует результаты обработки отчетов"""
        success_count = 0
        failed_reports = []

        for i, result in enumerate(results):
            report = pending_reports[i]

            if isinstance(result, Exception):
                # Неожиданная ошибка в задаче
                logger.error(
                    f"Задача по доставке отчета {report.report_id} "
                    f"неожиданно завершилась сбоем: {result}",
                    exc_info=True
                )
                failed_reports.append({
                    "report_id": report.report_id,
                    "user_id": report.user_id,
                    "error": "task_failed",
                    "message": str(result)
                })
            elif hasattr(result, 'success'):
                # Normal DeliveryResult
                if result.success:
                    success_count += 1
                else:
                    failed_reports.append({
                        "report_id": report.report_id,
                        "user_id": report.user_id,
                        "error": result.error_type,
                        "message": result.error_message
                    })
            else:
                # Неизвестный тип результата
                logger.error(f"Неизвестный тип результата для отчета {report.report_id}: {type(result)}")
                failed_reports.append({
                    "report_id": report.report_id,
                    "user_id": report.user_id,
                    "error": "unknown_result_type",
                    "message": f"Unexpected result type: {type(result)}"
                })

        logger.info(
            f"Отправлено {success_count}/{len(pending_reports)} отчетов. "
            f"{len(failed_reports)} не удалось отправить."
        )

        if failed_reports:
            logger.warning(f"Детали неудачных отчетов: {failed_reports}")

        return {
            "success_count": success_count,
            "failed_count": len(failed_reports),
            "failed_reports": failed_reports
        }



deepseek_api_client = DeepSeekClient(api_key=config.AI_API_KEY, base_url=config.AI_API_URL)
question_generator = QuestionGenerator(deepseek_api_client)
report_processor = ReportProcessor(question_generator, max_words_per_user=5)
weekly_report_service = WeeklyReportScheduler(report_processor)
