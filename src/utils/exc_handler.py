from aiogram.enums import ParseMode
from aiogram.types import Message

from src.translations import ERROR_MESSAGES
from exc import (
    EmptySpaceError, EmojiesNotAllowed,
    AlreadyExistsError,  TooShortError,
    TooLongError, InvalidCharactersError
)


async def nickname_exception_handler(
        message: Message,
        lang_code: str,
        error: Exception,
) -> None:
    """Обработчик исключений для валидации имени"""
    error_messages = {
        EmptySpaceError: "nickname_empty_space_error",
        EmojiesNotAllowed: "emojies_not_allowed_error",
        AlreadyExistsError: "nickname_already_exists_error",
        TooShortError: "nickname_too_short_error",
        TooLongError: "nickname_too_long_error",
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

async def intro_exception_handler(
        message: Message,
        lang_code: str,
        error: Exception
) -> None:
    """Обработчик исключений для валидации интро"""
    error_messages = {
        TooShortError: "intro_too_short_error",
        TooLongError: "intro_too_long_error"
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