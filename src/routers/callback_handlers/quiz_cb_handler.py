# from aiogram import Router, types, F
# from aiogram.enums import ParseMode
# from aiogram.filters import and_f
# from aiogram.fsm.context import FSMContext
# from aiogram.types import CallbackQuery
#
# from src.filters.approved import approved
# from src.keyboards.inline_keyboards import (
#     show_word_options_keyboard,
#     get_finish_button,
#     begin_daily_quiz_keyboard,
#     thought_time_keyboard
# )
# from src.translations import WEEKLY_QUIZ
# from src.utils.access_data import data_storage as ds
# from dependencies import get_x_api_client
# from exc import StorageDataException
# from logconf import opt_logger as log
#
# logger = log.setup_logger("weekly_message_cb_handler")
#
# router = Router(name=__name__)
#
#
# @router.callback_query(F.data.startswith("how_it_works:"), approved)
# async def how_it_works_handler(callback: types.CallbackQuery, state: FSMContext):
#     await callback.answer()
#     report_id = int(callback.data.split(":", 1)[1])
#
#     try:
#         data = await ds.get_storage_data(callback.from_user.id, state)
#         lang_code = data.get("lang_code")
#         await callback.message.edit_text(
#             text=WEEKLY_QUIZ["how_it_works"][lang_code],
#             reply_markup=begin_daily_quiz_keyboard(lang_code, report_id, False)
#         )
#
#     except StorageDataException:
#         return logger.error(f"User {callback.from_user.id} trying to acces data but doesn`t exist in DB")
#
#     except Exception as e:
#         return logger.error(f"Error in how_it_works_handler: {e}")
#
#
# @router.callback_query(
#     and_f(F.data.startswith("start_report:"), approved)
# )
# async def start_report_handler(
#     callback: types.CallbackQuery,
#     state: FSMContext,
# ):
#
#     await callback.answer()
#     database = await get_db()
#     data = await state.get_data()
#     is_active = data.get("is_active")
#     if not is_active: return await callback.answer("Your subscriotion on pause")
#
#     try:
#         user_id = callback.message.chat.id
#         # Извлекаю все ID слов конкретного отчета
#         report_id = int(callback.data.split(":", 1)[1])
#         word_ids = [row["word_id"] for row in await database.get_words_ids(report_id)]
#         lang_code = data.get(
#             "lang_code", (await database.get_user_info(user_id))["lang_code"]
#         )
#
#         if not word_ids:
#             await callback.answer(
#                 "Отчет не содержит слов для проверки.", show_alert=True
#             )
#             return
#
#         await state.update_data(
#             user_id=user_id,
#             report_id=report_id,
#             word_ids=word_ids,
#             current_index=0,
#             right_choices=[],
#             wrong_choices=[],
#             lang_code=lang_code,
#         )
#
#         await callback.message.edit_text(
#             text="Начинаем проверку знаний...",
#         )
#
#         # Передаем quiz_manager в send_question
#         await send_question(callback, state, database)
#
#     except Exception as e:
#         return logger.error(f"Ошибка в start_report_handler: {e}", exc_info=True)
#
#
# @router.callback_query(
#     and_f(lambda callback: callback.data.startswith("quiz:"), approved)
# )
# async def handle_word_quiz(callback: CallbackQuery, state: FSMContext):
#
#     await callback.answer()
#
#     database = await get_db()
#     data = await state.get_data()
#     lang_code = data.get("lang_code", "en")
#
#     parts = callback.data.split(":")
#     if len(parts) != 3:
#         return logger.error("Incorrect data of question")
#
#     word_id = int(parts[1])
#     selected_idx = int(parts[2])
#     word_data = await database.get_word_data(word_id)
#
#     if not word_data:
#         return logger.error("Ошибка: данные вопроса не найдены")
#
#     is_correct = selected_idx == word_data["correct_index"]
#     correct_word = word_data["options"][word_data["correct_index"]]
#     selected_word = word_data["options"][selected_idx]
#
#     if is_correct:
#         msg = WEEKLY_QUIZ["right_answer"][lang_code].format(correct_word=correct_word)
#         # Сохраняем правильное слово в data
#         r_choices = data.get("right_choices", [])
#         r_choices.append(correct_word)
#         await state.update_data(right_choices=r_choices)
#         await database.update_word_state(callback.from_user.id, correct_word, correct=True)
#
#     else:
#         msg = WEEKLY_QUIZ["wrong_answer"][lang_code].format(
#             selected_word=selected_word, correct_word=correct_word
#         )
#         # Сохраняем неправильное слово в data
#         w_choices = data.get("wrong_choices", [])
#         w_choices.append(word_data["word"])
#         await state.update_data(wrong_choices=w_choices)
#         await database.update_word_state(callback.from_user.id, correct_word, correct=False)
#
#     try:
#         # Отправляем результат ответа (используем user_id)
#         await callback.message.edit_reply_markup(reply_markup=None)
#         await callback.message.edit_text(
#             text=msg,
#             parse_mode=ParseMode.HTML,
#         )
#
#         # Переходим к следующему вопросу
#         next_idx = data.get("current_index", 0) + 1
#         await state.update_data(current_index=next_idx)
#         return await send_question(callback, state, database)
#
#     except Exception as e:
#         return logger.error(f"Ошибка при отправке сообщения: {e}")
#
#
# async def send_question(callback, state, database):
#
#     data = await state.get_data()
#     idx = data.get("current_index")
#     word_ids = data.get("word_ids")
#     user_id = data.get("user_id")
#     lang_code = data.get("lang_code", "en")
#
#     logger.debug(f"Data: {data}")
#
#     if not all(
#         key in data for key in ["current_index", "word_ids", "user_id", "lang_code"]
#     ):
#         return logger.error("Отсутствуют ключи в состоянии FSM (Redis)!")
#
#     if idx >= len(word_ids):
#
#         msg = WEEKLY_QUIZ["congradulations"][lang_code]
#         rights = (
#             ", ".join(data.get("right_choices", []))
#             or WEEKLY_QUIZ["no_rights"][lang_code]
#         )
#         wrongs = (
#             ", ".join(data.get("wrong_choices", []))
#             or WEEKLY_QUIZ["no_wrongs"][lang_code]
#         )
#         await callback.src.send_message(  # Используем tg-src-service из callback
#             chat_id=user_id,
#             text=msg.format(rights=rights, wrongs=wrongs),
#             reply_markup=get_finish_button(lang_code),
#         )
#         return await state.clear()
#
#     word_id = word_ids[idx]
#     word_data = await database.get_word_data(word_id)
#
#     if not word_data:
#         return logger.error("Ошибка: данные вопроса не найдены")
#     sentence, new_indx, total = word_data["sentence"], idx + 1, len(word_ids)
#     msg = WEEKLY_QUIZ["question_text"][lang_code]
#     await callback.src.send_message(
#         chat_id=user_id,
#         text=msg.format(idx=new_indx, total=total, sentence=sentence),
#         reply_markup=thought_time_keyboard(lang_code),
#     )
#
# @router.callback_query(and_f(F.data == 'thougth_time', approved))
# async def show_options_handler(callback: CallbackQuery, state: FSMContext):
#
#     await callback.answer()
#
#     database = await get_db()
#     data = await state.get_data()
#     idx = data.get("current_index")
#     word_ids = data.get("word_ids")
#     lang_code = data.get("lang_code")
#
#     word_id = word_ids[idx]
#     word_data = await database.get_word_data(word_id)
#
#     sentence, new_indx, total = word_data["sentence"], idx + 1, len(word_ids)
#     msg = WEEKLY_QUIZ["question_text"][lang_code]
#     await callback.message.edit_text(
#         text=msg.format(idx=new_indx, total=total, sentence=sentence),
#         reply_markup=show_word_options_keyboard(word_data),
#     )
#
#
# @router.callback_query(
#     and_f(lambda callback: callback.data.startswith("end_quiz"), approved)
# )
# async def do_nothing(callback: CallbackQuery):
#     await callback.answer()
#     await callback.message.delete()
#     return
