import re

import aiohttp.client_exceptions
import emoji
from typing import Union

from aiohttp import ClientResponse

from src.dependencies import get_gateway
from src.exc import (
    AlreadyExistsError, TooShortError,
    TooLongError, EmptySpaceError,
    InvalidCharactersError, EmojiesNotAllowed
)




async def validate_name(nickname: str) -> Union[True, Exception]:
    string_pattern = r"^(?=.*[a-zA-Z]{1,})(?=.*[\d]{0,})[a-zA-Z0-9]{1,15}$"

    x_api_client = await get_gateway()
    async with x_api_client() as session:
        resp: "ClientResponse" = await session.get('nickname_exists', nickname)
        if resp.status != 200: raise aiohttp.client_exceptions.ClientError
        data: dict = resp.json() # noqa
        if not data.get('exists'): raise AlreadyExistsError

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