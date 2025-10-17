from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.translations import ERROR_MESSAGES
from exc import EmptySpaceError, AlreadyExistsError, TooShortError, TooLongError, InvalidCharactersError


async def nickname_exception_handler(
        message: Message,
        state: FSMContext,
        error: Exception,
        lang_code: str
):
    """Обработчик исключений для валидации имени"""
    error_messages = {
        EmptySpaceError: "empty_space_error",
        AlreadyExistsError: "already_exists_error",
        TooShortError: "too_short_error",
        TooLongError: "too_long_error",
        InvalidCharactersError: "invalid_characters_error"
    }

    error_type = type(error)
    if error_type in error_messages:
        msg_key = error_messages[error_type]
        msg = ERROR_MESSAGES[msg_key][lang_code]
        await message.reply(text=msg, parse_mode=ParseMode.HTML)

    else:
        await message.reply(
            text=ERROR_MESSAGES["unknown_error"][lang_code],
            parse_mode=ParseMode.HTML
        )