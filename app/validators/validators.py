import re
import emoji
from typing import TYPE_CHECKING, Union

from exc import (
    AlreadyExistsError, TooShortError,
    TooLongError, EmptySpaceError,
    InvalidCharactersError, EmojiesNotAllowed
)

if TYPE_CHECKING:
    from app.services.database import DatabaseService



async def validate_name(nickname: str, db: "DatabaseService") -> Union[True, Exception]:
    string_pattern = r"^(?=.*[a-zA-Z]{1,})(?=.*[\d]{0,})[a-zA-Z0-9]{1,15}$"
    if await db.check_nickname_exists(nickname): raise AlreadyExistsError
    if any([ch in emoji.EMOJI_DATA for ch in nickname]): raise EmojiesNotAllowed
    if not 6 <= len(nickname): raise TooShortError
    if not len(nickname) <= 16: raise TooLongError
    if not re.sub(r"\s", "", nickname) == nickname: raise EmptySpaceError
    if not re.match(string_pattern, nickname): raise InvalidCharactersError
    return True

def validate_intro(intro: str) -> Union[True, Exception]:
    intro_wo_spaces = intro.replace(' ', '')
    if len(intro_wo_spaces) < 10: raise TooShortError
    if len(intro_wo_spaces) > 500: raise TooLongError
    return True