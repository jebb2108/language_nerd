from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.filters.approved import approved
from app.bot.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_go_back_keyboard,
    get_subscription_keyboard,
    get_profile_keyboard,
    get_edit_options,
    get_shop_keyboard, show_topic_keyboard
)
from app.bot.routers.callback_handlers.additional_cb_handler import router, logger
from app.bot.routers.commands.menu_commands import MultiSelection
from app.bot.translations import MESSAGES, EMOJI_SHOP, TRANSCRIPTIONS, EMOJI_TRANSCRIPTIONS
from app.bot.utils.access_data import data_storage as ds
from app.dependencies import get_db, get_redis_client
from config import config
from exc import StorageDataException
from logging_config import opt_logger as log

logger = log.setup_logger("main_menu_cb_handler", config.LOG_LEVEL)

router = Router(name=__name__)


@router.callback_query(
    and_f(F.data == "about", approved)
)
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """

    await callback.answer()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        is_active = data.get("is_active")
        if not is_active: return await callback.answer("Your subscription on pause")

        msg = MESSAGES["about"][lang_code]

        # Редактируем текущее сообщение
        await callback.message.edit_caption(
            caption=msg,
            reply_markup=get_go_back_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data, but doesn`t exist in DB")
        return await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        return logger.error(f"Error in about handler: {e}")


@router.callback_query(F.data == "go_back")
async def go_back_handler(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()
    database = await get_db()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        msg = f"{MESSAGES['welcome'][lang_code]}"

        if not await database.check_profile_exists(user_id):
            msg += MESSAGES["get_to_know"][lang_code]
        else:
            msg += MESSAGES["pin_me"][lang_code]

        await callback.message.edit_caption(
            caption=msg,
            reply_markup=get_on_main_menu_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data, but doesn`t exist in DB")
        return await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        return logger.error(f"Error in go_back handler: {e}")



@router.callback_query(F.data == "sub_details")
async def manage_subscription_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    redis_client = await get_redis_client()
    user_id = callback.from_user.id

    if await approved(callback):

        # После обновления Storage, делаю проверку на статус
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        is_active = data.get("is_active")

        if is_active:
            date_str = await redis_client.get(f"user_paid:{user_id}")
            cap = MESSAGES["active_sub_caption"][lang_code].format(date=date_str.split('T')[0])
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_subscription_keyboard(lang_code, True),
                parse_mode=ParseMode.HTML
            )
        else:
            cap = MESSAGES["resume_sub_caption"][lang_code]
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_subscription_keyboard(lang_code, False, True),
                parse_mode=ParseMode.HTML
            )
    else:
        # Уже по новой вызывается ds, чтобы вытащить lang_code
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        cap = MESSAGES["expired_sub_caption"][lang_code]
        await callback.message.edit_caption(
            caption=cap,
            reply_markup=get_subscription_keyboard(lang_code, False),
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data == "cancel_subscription")
async def cancel_subscription_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer("Subscription cancelled")

    database = await get_db()
    redis_client = await get_redis_client()
    await database.deactivate_subscription(callback.from_user.id)
    await state.clear()

    user_id = callback.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")
    await redis_client.delete(f"user_paid:{user_id}")
    is_active = False

    if await approved(callback):
        if is_active:
            date_str = await redis_client.get(f"user_paid:{user_id}")
            cap = MESSAGES["active_sub_caption"][lang_code].format(date=date_str.split('T')[0])
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_subscription_keyboard(lang_code, True),
                parse_mode=ParseMode.HTML
            )
        else:
            cap = MESSAGES["resume_sub_caption"][lang_code]
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_subscription_keyboard(lang_code, False, True),
                parse_mode=ParseMode.HTML
            )

    else:
        cap = MESSAGES["expired_sub_caption"][lang_code]
        await callback.message.edit_caption(
            caption=cap,
            reply_markup=get_subscription_keyboard(lang_code, False),
            parse_mode=ParseMode.HTML
        )


@router.callback_query(F.data == "resume_subscription")
async def resume_subscription_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer("Subscription resumed")

    database = await get_db()
    redis_client = await get_redis_client()
    await database.activate_subscription(callback.from_user.id)
    await state.clear()

    user_id = callback.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")
    is_active = True

    if await approved(callback):
        if is_active:
            date_str = await redis_client.get(f"user_paid:{user_id}")
            cap = MESSAGES["active_sub_caption"][lang_code].format(date=date_str.split('T')[0])
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_subscription_keyboard(lang_code, True),
                parse_mode=ParseMode.HTML
            )
        else:
            cap = MESSAGES["resume_sub_caption"][lang_code]
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_subscription_keyboard(lang_code, False, True),
                parse_mode=ParseMode.HTML
            )
    else:
        cap = MESSAGES["expired_sub_caption"][lang_code]
        await callback.message.edit_caption(
            caption=cap,
            reply_markup=get_subscription_keyboard(lang_code, False),
            parse_mode=ParseMode.HTML
        )


@router.callback_query(
    and_f(F.data == "profile", approved)
)
async def profile_handler(callback: CallbackQuery, state: FSMContext):
    """ Обработчик сведений о пользователе """
    await callback.answer()
    user_id = callback.from_user.id

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code", "en")
        is_active = data.get("is_active")
        if not is_active: return await callback.answer("Your subscription on pause")

        topics = [TRANSCRIPTIONS["topics"][topic][lang_code] for topic in data.get("topics").split(", ")]
        msg = MESSAGES["user_info"][lang_code].format(
            nickname=data.get("nickname", callback.from_user.username),
            age=data.get("age", 'not specified'),
            fluency=TRANSCRIPTIONS["fluency"][data.get("fluency")][lang_code],
            topic=", ".join(topics),
            language=TRANSCRIPTIONS["languages"][data.get("language")][lang_code],
            about=data.get("about", 'not specified'),
        )

        await callback.message.edit_caption(
            caption=msg,
            reply_markup=get_profile_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in profile_handler: {e}")


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



@router.callback_query(and_f(F.data.startswith("shop:"), approved))
async def shop_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    shop_indx, msg = int(callback.data.split(":")[1]), ""

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        msg = MESSAGES["shop_offer"][lang_code] + " "*10 + f"{shop_indx+1}/10\n\n"
        for k, v in EMOJI_SHOP["emojies"][shop_indx].items():
            msg += v + " " + EMOJI_TRANSCRIPTIONS[k][lang_code] + "\n"
        msg += "\n" + MESSAGES["shop_actions"][lang_code].format(description=EMOJI_SHOP["description"][shop_indx][lang_code])

        await callback.message.edit_caption(
            caption=msg,
            reply_markup=get_shop_keyboard(lang_code, shop_indx),
            parse_mode=ParseMode.HTML,
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

        if users_choice == "topics":
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

            await state.set_state(MultiSelection.waiting_selection)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in cancel_choosing_topic: {e}")


@router.callback_query(
    and_f(F.data.startswith("chtopic_"), MultiSelection.waiting_selection, approved)
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
        if len(new_topics) > 3: new_topics.pop(0)
        if users_choice == "endselection":
            new_topics.remove("endselection")
            profile_data = await ds.get_storage_data(user_id, state)

            if set(profile_data.get("topics").split(", ")) != set(new_topics):

                await database.change_topic(user_id, new_topics)
                await callback.answer(MESSAGES["topic_changed"][lang_code])
                await state.update_data(new_topics=[], topics=", ".join(new_topics))
                await state.update_data(topic=users_choice)
                return await go_back_handler(callback, state)

            await callback.answer(MESSAGES["fail_to_change"][lang_code])
            return await go_back_handler(callback, state)

        await state.update_data(new_topics=new_topics)
        await callback.message.edit_reply_markup(
            reply_markup=show_topic_keyboard(
                lang_code, selected_options=new_topics, new=True)
        )
        await state.set_state(MultiSelection.waiting_selection)

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in change_topic handler: {e}")
