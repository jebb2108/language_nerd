import re
from typing import TYPE_CHECKING
from .exc import EmptySpaceError, TooShortError, TooLongError, AlreadyExistsError, InvalidCharactersError
from .tokens import convert_token

if TYPE_CHECKING:
    from app.services.database import DatabaseService


async def validate_name(nickname: str, db: "DatabaseService") -> bool:
    string_pattern = r"^(?=.*[a-zA-Z]{1,})(?=.*[\d]{0,})[a-zA-Z0-9]{1,15}$"
    if await db.check_nickname_exists(nickname): raise AlreadyExistsError
    if not 6 <= len(nickname): raise TooShortError
    if not len(nickname) <= 16: raise TooLongError
    if not re.sub(r"\s", "", nickname) == nickname: raise EmptySpaceError
    if not re.match(string_pattern, nickname): raise InvalidCharactersError
    return True


async def validate_access(token: str, room_id: str) -> bool:
    user_data = convert_token(token)
    print(f"user data {user_data}")
    print(f"room_id from token: {user_data.get('room_id')}, room_id from query: {room_id}")
    if user_data.get("room_id") == room_id:
        print("Аутентификация прошла успешно")
        return True
    print("Некоректный token!")
    return False
