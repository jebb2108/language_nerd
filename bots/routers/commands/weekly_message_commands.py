import logging
from typing import Union

from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text, Bold
from aiogram.utils.markdown import html_decoration as hd
from aiogram.enums import ParseMode

from middlewares.resources_middleware import ResourcesMiddleware # noqa
from utils.message_mgr import MessageManager # noqa
from config import LOG_CONFIG # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='weekly_message_commands')

# Инициализация роутера
router = Router(name=__name__)


async def send_user_report(
        bot: Bot,
        user_id: int,
        report_id: int,
        database: ResourcesMiddleware,
) -> bool:
    """
    Отправляет пользователю его еженедельный отчет.
    """
    try:
        async with database.acquire_connection() as conn:
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
        state: FSMContext,
        database: ResourcesMiddleware,
):
    try:
        report_id = int(callback.data.split(":", 1)[1])
        async with database.acquire_connection() as conn:
            words = await conn.fetch(
                "SELECT word_id FROM report_words WHERE report_id = $1",
                report_id
            )

        if not words:
            await callback.answer("Отчет не содержит слов для проверки.", show_alert=True)
            return

        # Создаем и сохраняем менеджер сообщений в состоянии
        quiz_manager = MessageManager(bot=callback.bot, state=state)
        chat_id = callback.message.chat.id

        await state.update_data(
            report_id=report_id,
            word_ids=[row["word_id"] for row in words],
            current_index=0,
            chat_id=chat_id,
            db_pool=database,
            quiz_manager=quiz_manager  # Сохраняем менеджер в state
        )

        await quiz_manager.send_message_with_save(
            chat_id=chat_id,
            text="Начинаем проверку знаний..."
        )

        # Передаем quiz_manager в send_question
        await send_question(state, quiz_manager)
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка в start_report_handler: {e}", exc_info=True)
        await callback.answer("Ошибка запуска проверки", show_alert=True)


async def send_question(
        state: FSMContext,
        quiz_manager: MessageManager
):
    data = await state.get_data()
    idx = data.get("current_index")
    word_ids = data.get("word_ids")
    chat_id = data.get("chat_id")
    db_pool = data.get("db_pool")

    if not all(key in data for key in ["current_index", "word_ids", "chat_id", "db_pool"]):
        logger.error("Отсутствуют ключи в состоянии FSM!")
        return

    if idx >= len(word_ids):
        await quiz_manager.delete_previous_messages(chat_id)
        await quiz_manager.bot.send_message_with_save(  # Используем bot из менеджера
            chat_id=chat_id,
            text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам за эту неделю."
        )
        await state.clear()
        return

    word_id = word_ids[idx]
    async with db_pool.acquire_connection() as conn:
        word_data = await conn.fetchrow(
            "SELECT * FROM report_words WHERE word_id = $1",
            word_id
        )

    if not word_data:
        await quiz_manager.send_message_wth_save(
            chat_id=chat_id,
            text="Ошибка: данные вопроса не найдены."
        )
        return

    question_text = (
        f"❓ Вопрос {idx + 1}/{len(word_ids)}\n\n"
        f"{word_data['sentence']}\n\n"
        "Выберите правильный вариант:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for opt_idx, option in enumerate(word_data["options"]):
        cb = f"quiz:{word_id}:{opt_idx}"
        row.append(InlineKeyboardButton(text=option, callback_data=cb))
        if len(row) >= 2:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)

    await quiz_manager.send_message_with_save(
        chat_id=chat_id,
        text=question_text,
        reply_markup=keyboard
    )


@router.callback_query(lambda callback: callback.data.startswith("quiz:"))
async def handle_word_quiz(
        callback: CallbackQuery,
        state: FSMContext,
):
    try:
        data = await state.get_data()
        db_pool = data.get("db_pool")
        chat_id = callback.message.chat.id
        quiz_manager = data.get("quiz_manager")  # Получаем менеджер из состояния

        if not quiz_manager:
            logger.error("QuizManager отсутствует в состоянии!")
            await callback.answer("Ошибка системы", show_alert=True)
            return

        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Некорректные данные вопроса.", show_alert=True)
            return

        word_id = int(parts[1])
        selected_idx = int(parts[2])

        async with db_pool.acquire_connection() as conn:
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
            msg = Text(
                "✅ Правильно! Отличная работа!\n\n",
                Bold("Слово: "), hd.quote(record['word'])
            ).as_markdown()
        else:
            msg = Text(
                "❌ К сожалению, неверно.\n\n",
                Bold("Ваш ответ: "), hd.quote(selected_word), "\n",
                Bold("Правильный ответ: "), hd.quote(correct_word), "\n",
                Bold("Слово: "), hd.quote(record['word'])
            ).as_markdown()

        await callback.answer()

        # Убираем кнопки с текущего сообщения
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Ошибка при удалении кнопок: {e}")

        # Отправляем результат ответа (используем chat_id)
        await quiz_manager.send_message_wth_save(
            chat_id=chat_id,
            text=msg,
            parse_mode=ParseMode.HTML
        )

        # Переходим к следующему вопросу
        next_idx = data.get("current_index", 0) + 1
        await state.update_data(current_index=next_idx)

        # Передаем только quiz_manager
        await send_question(state, quiz_manager)

    except Exception as e:
        logger.error(f"Ошибка в handle_word_quiz: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке ответа", show_alert=True)


@router.callback_query()  # Без фильтров, перехватывает все запросы обратного вызова
async def handle_unhandled_callback_query(callback: types.CallbackQuery):
    logger.warning(f"Получен необработанный запрос обратного вызова: {callback.data}")
    await callback.answer("Извините, я не понял эту команду.", show_alert=True)