import json
import asyncio
from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN_MAIN, logger # noqa

router = Router(name=__name__)


async def send_telegram_message(
        session,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str = "Markdown"
):
    """Универсальная функция отправки сообщений в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN_MAIN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup.to_json()

    try:
        async with session.post(url, json=payload, timeout=30) as response:
            if response.status != 200:
                response_text = await response.text()
                logger.error(f"Telegram API error: {response.status} - {response_text}")
            return response.status == 200
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False


async def send_user_report(db_pool, session, user_id, report_id):
    """Отправляет отчет пользователю с интерактивными кнопками"""
    try:
        # Получаем слова отчета
        async with db_pool.acquire() as conn:
            words = await conn.fetch(
                "SELECT word_id, word, sentence, options, correct_index "
                "FROM report_words WHERE report_id = $1",
                report_id
            )

        if not words:
            logger.warning(f"No words found for report {report_id}")
            return False

        # Отправляем вступительное сообщение
        intro_message = (
            "📚 *Ваши слова недели для практики:*\n\n"
            "Выберите правильный вариант для каждого предложения. "
            "Буду отправлять вопросы по одному."
        )
        await send_telegram_message(session, user_id, intro_message)

        # Отправляем каждое слово отдельным сообщением с кнопками
        for i, record in enumerate(words, 1):
            # Создаем инлайн-кнопки
            keyboard = []
            for idx, option in enumerate(record["options"]):
                # Формируем уникальный callback_data
                callback_data = json.dumps({
                    "type": "word_quiz",
                    "word_id": record["word_id"],
                    "selected": idx,
                    "correct": record["correct_index"],
                    "total": len(words),
                    "current": i,
                })
                keyboard.append([InlineKeyboardButton(
                    text=option,
                    callback_data=callback_data
                )])

            # Создаем клавиатуру
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            # Формируем сообщение
            message = f"*Вопрос {i}/{len(words)}:*\n{record['sentence']}"

            # Отправляем сообщение
            await send_telegram_message(
                session,
                user_id,
                message,
                reply_markup=reply_markup
            )

            # Задержка между сообщениями
            await asyncio.sleep(0.5)

        return True

    except Exception as e:
        logger.error(f"Error sending interactive report to {user_id}: {e}")
        return False


@router.callback_query(lambda c: json.loads(c.data)["type"] == "word_quiz")
async def handle_word_quiz(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответы на вопросы со словами"""
    try:
        data = json.loads(callback.data)
        word_id = data["word_id"]
        selected = data["selected"]
        correct_idx = data["correct"]

        # Проверяем ответ
        if selected == correct_idx:
            message = "✅ Правильно! Отличная работа!"
        else:
            # Получаем правильный ответ из БД
            async with db_pool.acquire() as conn:
                record = await conn.fetchrow(
                    "SELECT options, correct_index FROM report_words WHERE word_id = $1",
                    word_id
                )
            correct_word = record["options"][record["correct_index"]]
            message = f"❌ К сожалению, неверно. Правильный ответ: {correct_word}"

        # Отправляем результат
        await callback.answer()
        await callback.message.reply(
            message,
            reply_to_message_id=callback.message.message_id
        )

        # TODO: Реализовать логику отправки следующего вопроса

    except Exception as e:
        logger.error(f"Error handling quiz callback: {e}")