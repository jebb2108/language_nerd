import aiohttp.client_exceptions
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile
from aiohttp import ClientResponse

from src.config import config
from src.dependencies import get_gateway
from src.exc import StorageDataException
from src.filters.approved import approved
from src.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
    get_subscription_keyboard,
    get_profile_keyboard,
    get_shop_keyboard,
    about_me_keyboard
)
from src.logconf import opt_logger as log
from src.translations import MESSAGES, EMOJI_SHOP, TRANSCRIPTIONS, EMOJI_TRANSCRIPTIONS
from src.utils.access_data import data_storage as ds, MultiSelection

logger = log.setup_logger("main_menu_cb_handler")

router = Router(name=__name__)


@router.callback_query(and_f(F.data == "start_main_page", approved))
async def start_main_page_handler(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, создавая новое сообщение
    """
    await callback.answer()
    await callback.message.delete()

    user_id = callback.from_user.id

    gateway = await get_gateway()
    async with gateway() as session:
        profile_exists = await session.get('profile_exists', user_id)

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        msg = f"{MESSAGES['welcome'][lang_code]}"

        if not profile_exists:
            msg += MESSAGES["get_to_know"][lang_code]
        else:
            msg += MESSAGES["pin_me"][lang_code]

        image_from_file = FSInputFile(config.ABS_PATH_TO_IMG_ONE)
        await callback.message.answer_photo(
            photo=image_from_file,
            caption=msg,
            reply_markup=get_on_main_menu_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data, but doesn`t exist in DB")
        return await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        return logger.error(f"Error in go_back handler: {e}")


@router.callback_query(F.data == "go_back")
async def go_back_handler(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()
    await state.set_state(MultiSelection.ended_change)

    profile_exists = None
    user_id = callback.from_user.id

    gateway = await get_gateway()
    async with gateway() as session:
        profile_exists = await session.get('profile_exists', user_id)

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        msg = f"{MESSAGES['welcome'][lang_code]}"

        if not profile_exists:
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
            reply_markup=about_me_keyboard(lang_code),
            parse_mode=ParseMode.HTML,
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to acces data, but doesn`t exist in DB")
        return await callback.message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        return logger.error(f"Error in about handler: {e}")

@router.callback_query(
    and_f(F.data == "profile", approved)
)
async def profile_handler(callback: CallbackQuery, state: FSMContext):
    """ Обработчик сведений о пользователе """
    await callback.answer()
    user_id = callback.from_user.id

    try:
        await state.clear()
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code", "en")
        is_active = data.get("is_active")
        if not is_active: return await callback.answer("Your subscription on pause")


        nickname = data.get("nickname", callback.from_user.username)
        sidebar = "=" * (17 - len(nickname))
        formated_nickname = sidebar + " " + nickname + " " + sidebar
        topics = [TRANSCRIPTIONS["topics"][topic][lang_code] for topic in data.get("topics").split(", ")]
        msg = MESSAGES["user_info"][lang_code].format(
            nickname=formated_nickname,
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


@router.callback_query(F.data == "go_back")
async def go_back_handler(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    await callback.answer()
    await state.set_state(MultiSelection.ended_change)

    user_id = callback.from_user.id

    gateway = await get_gateway()
    async with gateway() as session:
        profile_exists = await session.get('profile_exists', user_id)

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        msg = f"{MESSAGES['welcome'][lang_code]}"

        if not profile_exists:
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


@router.callback_query(F.data == "sub_details")
async def manage_subscription_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    user_id = callback.from_user.id

    if await approved(callback, state):

        # После обновления Storage, делаю проверку на статус
        gateway = await get_gateway()
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        is_active = data.get("is_active")
        due_to = data.get('due_to')

        if is_active:
            cap = MESSAGES["active_sub_caption"][lang_code].format(date=due_to.split('T')[0])
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

    user_id = callback.from_user.id

    gateway = await get_gateway()
    async with gateway() as session:
        await session.post('deactivate_subscription', user_id)

    await state.clear()

    user_id = callback.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")
    due_to = data.get('due_to')
    is_active = False

    if await approved(callback):
        if is_active:
            cap = MESSAGES["active_sub_caption"][lang_code].format(date=due_to.split('T')[0])
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

    user_id = callback.from_user.id
    gateway = await get_gateway()
    async with gateway() as session:
        resp: "ClientResponse" = await session.post('activate_subscription', user_id)
        if resp.status != 200: raise aiohttp.client_exceptions.ClientError

    await state.clear()

    user_id = callback.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")
    due_to = data.get('due_to')
    is_active = True

    if await approved(callback):
        if is_active:
            cap = MESSAGES["active_sub_caption"][lang_code].format(date=due_to.split('T')[0])
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


