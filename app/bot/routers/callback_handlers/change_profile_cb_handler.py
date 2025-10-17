from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.filters.approved import approved
from app.bot.keyboards.inline_keyboards import (
    get_edit_options, choose_nickname_keyboard,
    show_topic_keyboard, show_fluency_keyboard,
    show_language_keyboard
)
from app.bot.routers.callback_handlers.main_menu_cb_handler import go_back_handler
from app.bot.translations import MESSAGES, TRANSCRIPTIONS
from app.bot.utils.access_data import data_storage as ds, MultiSelection
from app.dependencies import get_db
from exc import StorageDataException
from logging_config import opt_logger as log

logger = log.setup_logger("additional_cb_handler")

router = Router(name=__name__)


@router.callback_query(and_f(F.data == "edit_profile", approved))
async def edit_profile_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    user_id = callback.from_user.id
    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        await callback.message.edit_caption(
            caption=MESSAGES["change_profile_options"][lang_code],
            reply_markup=get_edit_options(lang_code)
        )


    except Exception as e:
        logger.error(f"Error in shop_handler: {e}")


@router.callback_query(F.data.startswith("profile_change:"))
async def profile_change_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        users_choice = callback.data.split(":")[1]

        if users_choice == 'nickname':
            current_nickname = data.get("nickname", False)
            if current_nickname:
                msg = MESSAGES["current_nickname"][lang_code].format(nickname=current_nickname)
            else:
                msg = MESSAGES["no_nickname"][lang_code]

            await callback.message.edit_caption(
                caption=msg, parse_mode=ParseMode.HTML
            )
            await callback.message.edit_reply_markup(
                reply_markup=choose_nickname_keyboard(lang_code)
            )
            await state.set_state(MultiSelection.waiting_nickname)

        elif users_choice == "language":
            current_language = data.get("language")
            msg = MESSAGES["current_lang"][lang_code].format(language=current_language)
            await callback.message.edit_caption(caption=msg)
            await callback.message.edit_reply_markup(reply_markup=show_language_keyboard(new=True))
            await state.set_state(MultiSelection.waiting_language)


        elif users_choice == "topics":
            all_topics = data.get("topics").split(', ')
            topics = [TRANSCRIPTIONS["topics"][topic][lang_code] for topic in all_topics]

            msg = MESSAGES["current_topic"][lang_code].format(
                topic=", ".join(topics)
            )
            await state.update_data(new_topics=[])
            await callback.message.edit_caption(
                caption=msg, reply_markup=show_topic_keyboard(
                    lang_code, selected_options=[], new=True)
                , parse_mode=ParseMode.HTML
            )

            await state.set_state(MultiSelection.waiting_topic)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in cancel_choosing_topic: {e}")


@router.callback_query(
    and_f(F.data.startswith("chlang_"), MultiSelection.waiting_language, approved)
)
async def change_lang_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        users_choice = callback.data.split('_', 1)[1]
        await state.update_data(new_lang=users_choice)
        await callback.message.edit_reply_markup(
            reply_markup=show_fluency_keyboard(lang_code, True)
        )
        return await state.set_state(MultiSelection.waiting_fluency)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in change_lang_handler: {e}")


@router.callback_query(
    and_f(F.data.startswith("chfluency_"), MultiSelection.waiting_fluency, approved)
)
async def change_fluency_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    database = await get_db()
    user_id = callback.from_user.id
    users_choice = callback.data.split('_', 1)[1]
    try:
        data = await ds.get_storage_data(user_id, state)
        new_language = data.get("new_lang")
        await database.change_language(user_id, new_language, int(users_choice))
        await state.set_state(MultiSelection.ended_change)
        return await go_back_handler(callback, state)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in change_fluency_handler: {e}")



@router.callback_query(
    and_f(F.data.startswith("chtopic_"), MultiSelection.waiting_topic, approved)
)
async def change_topic_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    database = await get_db()
    user_id = callback.from_user.id
    users_choice = callback.data.split("_")[1]

    try:
        data = await state.get_data()
        lang_code = data.get("lang_code")
        new_topics = data.get("new_topics", [])
        if users_choice not in new_topics:
            new_topics.append(users_choice)
        if len(new_topics) > 3:
            if users_choice != "endselection":
                new_topics.pop(0)
        if users_choice == "endselection":
            new_topics.remove("endselection")
            if not new_topics: return
            profile_data = await ds.get_storage_data(user_id, state)
            if set(profile_data.get("topics").split(", ")) != set(new_topics):

                await database.change_topic(user_id, new_topics)
                await callback.answer(MESSAGES["topic_changed"][lang_code])
                await state.update_data(new_topics=[], topics=", ".join(new_topics))
                await state.set_state(MultiSelection.ended_change)
                return await go_back_handler(callback, state)

            await callback.answer(MESSAGES["fail_to_change"][lang_code])
            return await go_back_handler(callback, state)

        await state.update_data(new_topics=new_topics)
        await callback.message.edit_reply_markup(
            reply_markup=show_topic_keyboard(
                lang_code, selected_options=new_topics, new=True)
        )
        await state.set_state(MultiSelection.waiting_topic)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in change_topic handler: {e}")
