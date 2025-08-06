import asyncio
from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text, Bold
from aiogram.utils.markdown import html_decoration as hd

from config import logger # noqa

router = Router(name=__name__)


async def send_user_report(resources, bot: Bot, user_id: int, report_id: int) -> bool:
    """Отправляет пользователю его отчет"""
    try:
        async with resources.db_pool.acquire() as conn:
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

        message_text = (
            f"📊 Ваш еженедельный отчет по изученным словам:\n\n"
            f"Всего слов: {len(words)}\n\n"
            "Для начала проверки нажмите кнопку ниже 👇"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Начать проверку знаний",
                callback_data=f"start_report:{report_id}"
            )]
        ])

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
async def start_report_handler(
        callback: types.CallbackQuery,
        state: FSMContext
):
    """Обработчик начала прохождения отчета"""
    try:
        # Получаем resources из data (добавлено middleware)
        resources = callback.conf["resources"]
        report_id = int(callback.data.split(":")[1])

        async with resources.db_pool.acquire() as conn:
            words = await conn.fetch(
                "SELECT word_id FROM report_words WHERE report_id = $1",
                report_id
            )

        if not words:
            await callback.answer("Отчет не содержит слов для проверки.", show_alert=True)
            return

        await state.clear()
        await state.update_data({
            "report_id": report_id,
            "word_ids": [word["word_id"] for word in words],
            "current_index": 0,
            "chat_id": callback.message.chat.id,
            "resources": resources  # Сохраняем в состоянии
        })

        await send_question(state, callback.bot, resources)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error starting report: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при запуске отчета.", show_alert=True)


async def send_question(state: FSMContext, bot: Bot, resources):
    """Отправляет текущий вопрос пользователю"""
    try:
        data = await state.get_data()
        current_index = data["current_index"]
        word_ids = data["word_ids"]
        chat_id = data["chat_id"]

        if current_index >= len(word_ids):
            await bot.send_message(
                chat_id=chat_id,
                text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам."
            )
            await state.clear()
            return

        word_id = word_ids[current_index]

        async with resources.db_pool.acquire() as conn:
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

        question_text = (
            f"❓ Вопрос {current_index + 1}/{len(word_ids)}\n\n"
            f"{word_data['sentence']}\n\n"
            "Выберите правильный вариант:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        row = []
        for idx, option in enumerate(word_data["options"]):
            callback_data = f"quiz:{word_id}:{idx}"
            row.append(InlineKeyboardButton(
                text=option,
                callback_data=callback_data
            ))
            if len(row) >= 2:
                keyboard.inline_keyboard.append(row)
                row = []

        if row:
            keyboard.inline_keyboard.append(row)

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
    return callback.data.startswith("quiz:")


@router.callback_query(quiz_callback_filter)
async def handle_word_quiz(
        callback: types.CallbackQuery,
        state: FSMContext
):
    """Обрабатывает ответы на вопросы со словами"""
    try:
        # Получаем resources из состояния
        data = await state.get_data()
        resources = data.get("resources")

        if not resources:
            logger.error("Resources not found in state!")
            await callback.answer("Внутренняя ошибка: ресурсы не найдены", show_alert=True)
            return

        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Некорректные данные вопроса.", show_alert=True)
            return

        word_id = int(parts[1])
        selected_idx = int(parts[2])

        async with resources.db_pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT word, options, correct_index FROM report_words WHERE word_id = $1",
                word_id
            )

        if not record:
            await callback.answer("Ошибка: данные вопроса не найдены.", show_alert=True)
            return

        is_correct = selected_idx == record["correct_index"]
        correct_word = record["options"][record["correct_index"]]
        selected_word = record["options"][selected_idx]

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

        await callback.answer()
        await callback.message.reply(
            text=message,
            parse_mode="MarkdownV2"
        )

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        data = await state.get_data()
        current_index = data.get("current_index", 0) + 1

        if current_index >= len(data.get("word_ids", [])):
            await callback.bot.send_message(
                chat_id=data["chat_id"],
                text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам."
            )
            await state.clear()
        else:
            await state.update_data(current_index=current_index)
            # Получаем resources из состояния
            await send_question(state, callback.bot, data["resources"])

    except Exception as e:
        logger.error(f"Error handling quiz callback: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке ответа.", show_alert=True)