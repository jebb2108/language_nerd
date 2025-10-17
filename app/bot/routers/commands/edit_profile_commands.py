from aiogram import Router
from aiogram.filters import and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.filters.approved import approved
from app.bot.translations import MESSAGES
from app.bot.utils.access_data import MultiSelection
from app.bot.utils.exc_handler import nickname_exception_handler
from app.dependencies import get_db
from app.validators.validators import validate_name
from exc import AlreadyExistsError, TooShortError, TooLongError, InvalidCharactersError, EmptySpaceError
from logging_config import opt_logger as log

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
    database = await get_db()
    data = await state.get_data()
    lang_code = data.get("lang_code")
    try:
        await validate_name(new_nickname, database)
    except (
        AlreadyExistsError,
        TooShortError,
        TooLongError,
        InvalidCharactersError,
        EmptySpaceError
    ) as e:
        await state.set_state(MultiSelection.waiting_nickname)
        return await nickname_exception_handler(message, lang_code, e)
    else:
        msg = MESSAGES['welcome'][lang_code]+MESSAGES["get_to_know"][lang_code]
        await message.edit_caption(caption=msg)
        await state.update_data(nickname=new_nickname)
        await message.answer(text=MESSAGES["nickname_change_succeeded"][lang_code])
        await database.change_nickname(user_id, new_nickname)
        return await state.set_state(MultiSelection.ended_change)





