import aiohttp.client_exceptions
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiohttp import ClientResponse

from src.filters.approved import approved
from src.keyboards.inline_keyboards import get_menu_keyboard
from src.translations import MESSAGES
from src.utils.access_data import MultiSelection
from src.utils.exc_handler import nickname_exception_handler, intro_exception_handler
from src.validators.validators import validate_name, validate_intro
from src.exc import AlreadyExistsError, TooShortError, TooLongError, InvalidCharactersError, EmptySpaceError, \
    EmojiesNotAllowed
from src.logconf import opt_logger as log
from src.dependencies import get_gateway

router = Router(name=__name__)
logger = log.setup_logger("edit_profile_commands")


@router.message(and_f(MultiSelection.waiting_nickname, approved))
async def edit_nickname_handler(message: Message, state: FSMContext) -> None:
    """
    Создает цикл проверки на валидность введенного нийнема
    :param message: Объект сообщения
    :param state: Finite Machine State
    :return: None
    """
    user_id = message.from_user.id
    new_nickname = message.text.strip()
    data = await state.get_data()
    lang_code = data.get("lang_code")
    try:
        await validate_name(new_nickname)
    except (
        AlreadyExistsError,
        EmojiesNotAllowed,
        TooShortError,
        TooLongError,
        InvalidCharactersError,
        EmptySpaceError
    ) as e:
        await state.set_state(MultiSelection.waiting_nickname)
        return await nickname_exception_handler(message, lang_code, e)
    else:
        await state.update_data(nickname=new_nickname)
        await message.answer(
            text=MESSAGES["nickname_change_succeeded"][lang_code],
            reply_markup=get_menu_keyboard(lang_code),
            parse_mode=ParseMode.HTML
        )

        gateway = await get_gateway()
        async with gateway() as session:
            resp: "ClientResponse" = await session.post('update_nickname', user_id, new_nickname)
            if resp.status != 200: raise aiohttp.client_exceptions.ClientError

        return await state.set_state(MultiSelection.ended_change)


@router.message(and_f(MultiSelection.waiting_intro, approved))
async def edit_intro_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_intro = message.text.strip()
    data = await state.get_data()
    lang_code = data.get("lang_code")
    try:
        validate_intro(new_intro)
    except (TooShortError, TooLongError) as e:
        await state.set_state(MultiSelection.waiting_intro)
        return await intro_exception_handler(message, lang_code, e)
    else:
        await state.update_data(intro=new_intro)
        await message.answer(
            text=MESSAGES["intro_change_succeeded"][lang_code],
            reply_markup=get_menu_keyboard(lang_code),
            parse_mode=ParseMode.HTML
        )

        gateway = await get_gateway()
        async with gateway() as session:
            resp: "ClientResponse" = await session.post('update_intro', user_id, new_intro)
            if resp.status != 200: raise aiohttp.client_exceptions.ClientError

        return await state.set_state(MultiSelection.ended_change)





