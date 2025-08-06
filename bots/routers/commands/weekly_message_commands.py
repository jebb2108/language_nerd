import asyncio
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text, Bold, Italic  # Для безопасного форматирования
from aiogram.utils.markdown import html_decoration as hd  # Для HTML-экранирования

from config import db_pool, BOT_TOKEN_MAIN, logger # noqa

router = Router(name=__name__)


async def send_user_report(db_pool, bot, user_id, report_id):
    """Отправляет пользователю его отчет"""
    try:
        # Получаем данные отчета
        async with db_pool.acquire() as conn:
            report = await conn.fetchrow(
                "SELECT * FROM weekly_reports WHERE report_id = $1",
                report_id
            )
            words = await conn.fetch(
                "SELECT * FROM report_words WHERE report_id = $1",
                report_id
            )

        if not report or not words:
            logger.warning(f"No report data found for report_id: {report_id}")
            return False

        # Формируем сообщение
        message_text = (
            f"📊 Ваш еженедельный отчет по изученным словам:\n\n"
            f"Всего слов: {len(words)}\n\n"
            "Для начала проверки нажмите кнопку ниже 👇"
        )

        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Начать проверку знаний",
                callback_data=f"start_report:{report_id}"
            )]
        ])

        # Отправляем сообщение
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=keyboard
        )

        return True

    except Exception as e:
        logger.error(f"Error sending interactive report to {user_id}: {e}")
        return False


@router.callback_query(lambda c: c.data.startswith("start_report:"))
async def start_report_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик начала прохождения отчета"""
    try:
        report_id = int(callback.data.split(":")[1])

        # Получаем список слов в отчете
        async with db_pool.acquire() as conn:
            words = await conn.fetch(
                "SELECT word_id FROM report_words WHERE report_id = $1",
                report_id
            )

        if not words:
            await callback.answer("Отчет не содержит слов для проверки.", show_alert=True)
            return

        # Сохраняем состояние в виде словаря
        await state.clear()
        await state.update_data({
            "report_id": report_id,
            "word_ids": [word["word_id"] for word in words],
            "current_index": 0,
            "chat_id": callback.message.chat.id
        })

        # Отправляем первый вопрос
        await send_question(state, callback.bot)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error starting report: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при запуске отчета.", show_alert=True)


async def send_question(state: FSMContext, bot: types.Bot):
    """Отправляет текущий вопрос пользователю"""
    try:
        data = await state.get_data()
        current_index = data["current_index"]
        word_ids = data["word_ids"]
        chat_id = data["chat_id"]

        if current_index >= len(word_ids):
            # Все вопросы пройдены
            await bot.send_message(
                chat_id=chat_id,
                text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам."
            )
            await state.clear()
            return

        word_id = word_ids[current_index]

        # Получаем данные слова
        async with db_pool.acquire() as conn:
            word_data = await conn.fetchrow(
                "SELECT * FROM report_words WHERE word_id = $1",
                word_id
            )

        if not word_data:
            await bot.send_message(
                chat_id=chat_id,
                text="Ошибка: данные вопроса не найдены."
            )
            return

        # Формируем сообщение с вопросом
        question_text = (
            f"❓ Вопрос {current_index + 1}/{len(word_ids)}\n\n"
            f"{word_data['sentence']}\n\n"
            "Выберите правильный вариант:"
        )

        # Создаем клавиатуру с вариантами ответов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        row = []
        for idx, option in enumerate(word_data["options"]):
            # Используем компактный формат для экономии места
            callback_data = f"quiz:{word_id}:{idx}"
            row.append(InlineKeyboardButton(
                text=option,
                callback_data=callback_data
            ))
            # Добавляем новую строку после каждых 2 кнопок
            if len(row) >= 2:
                keyboard.inline_keyboard.append(row)
                row = []

        # Добавляем последнюю неполную строку
        if row:
            keyboard.inline_keyboard.append(row)

        # Отправляем вопрос
        await bot.send_message(
            chat_id=chat_id,
            text=question_text,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error sending question: {e}", exc_info=True)
        data = await state.get_data()
        if "chat_id" in data:
            await bot.send_message(
                chat_id=data["chat_id"],
                text="Произошла ошибка при загрузке вопроса."
            )


def quiz_callback_filter(callback: types.CallbackQuery):
    """Фильтр для обработки ответов на вопросы"""
    return callback.data.startswith("quiz:")


@router.callback_query(quiz_callback_filter)
async def handle_word_quiz(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответы на вопросы со словами"""
    try:
        # Разбираем callback_data
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Некорректные данные вопроса.", show_alert=True)
            return

        word_id = int(parts[1])
        selected_idx = int(parts[2])

        # Получаем данные слова
        async with db_pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT word, options, correct_index FROM report_words WHERE word_id = $1",
                word_id
            )

        if not record:
            await callback.answer("Ошибка: данные вопроса не найдены.", show_alert=True)
            return

        # Проверяем ответ
        is_correct = selected_idx == record["correct_index"]
        correct_word = record["options"][record["correct_index"]]
        selected_word = record["options"][selected_idx]

        # Формируем ответ с безопасным форматированием
        if is_correct:
            message = Text(
                "✅ Правильно! Отличная работа!\n\n",
                Bold("Слово: "), hd.quote(record['word'])
            ).as_markdown()
        else:
            message = Text(
                "❌ К сожалению, неверно.\n\n",
                Bold("Ваш ответ: "), hd.quote(selected_word), "\n",
                Bold("Правильный ответ: "), hd.quote(correct_word), "\n",
                Bold("Слово: "), hd.quote(record['word'])
            ).as_markdown()

        # Отправляем результат
        await callback.answer()
        await callback.message.reply(
            text=message,
            parse_mode="MarkdownV2"
        )

        # Пытаемся убрать клавиатуру с вопросом
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass  # Не критично, если не получилось

        # Обновляем состояние и отправляем следующий вопрос
        data = await state.get_data()
        current_index = data.get("current_index", 0) + 1

        # Проверяем, не закончились ли вопросы
        if current_index >= len(data.get("word_ids", [])):
            await callback.bot.send_message(
                chat_id=data["chat_id"],
                text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам."
            )
            await state.clear()
        else:
            await state.update_data(current_index=current_index)
            await send_question(state, callback.bot)

    except Exception as e:
        logger.error(f"Error handling quiz callback: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке ответа.", show_alert=True)