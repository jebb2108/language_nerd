from typing import Union, Optional

from pydantic import BaseModel, Field


class UserDictionaryRequest(BaseModel):
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    word: Union[str, None] = Field(None, description="Слово, которое нужно добавить в словарь")
    part_of_speech: Union[str, None] = Field(None, description="Часть речи слова")
    translation: Union[str, None] = Field(None, description="Перевод слова")

    source: Optional[str] = Field(
        default="api", description="Источник запроса (api, bot, etc)"
    )
