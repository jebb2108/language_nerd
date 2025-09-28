from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


class Language(str, Enum):
    """Поддерживаемые языки"""

    RU = "ru"
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"


class Topic(str, Enum):
    """Темы для общения"""

    GENERAL = "general"
    MUSIC = "music"
    MOVIES = "movies"
    SPORTS = "sports"
    TECHNOLOGY = "technology"
    TRAVEL = "travel"
    GAMES = "games"


class UserProfile(BaseModel):
    """
    Модель профиля пользователя (для базы данных).
    """

    user_id: str
    username: Optional[str]
    age: Optional[int]
    language: List[Language]
    interests: List[Topic]
    created_at: datetime
    is_active: bool = True
