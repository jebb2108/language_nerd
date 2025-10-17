import re

from exc import AlreadyExistsError, TooShortError, TooLongError, EmptySpaceError, InvalidCharactersError


async def validate_name(nickname: str, db: "DatabaseService") -> bool:
    string_pattern = r"^(?=.*[a-zA-Z]{1,})(?=.*[\d]{0,})[a-zA-Z0-9]{1,15}$"
    if await db.check_nickname_exists(nickname): raise AlreadyExistsError
    if not 6 <= len(nickname): raise TooShortError
    if not len(nickname) <= 16: raise TooLongError
    if not re.sub(r"\s", "", nickname) == nickname: raise EmptySpaceError
    if not re.match(string_pattern, nickname): raise InvalidCharactersError
    return True
