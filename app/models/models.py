from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Union
from datetime import datetime
from enum import Enum


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


class UserDictionaryRequest(BaseModel):
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    word: Union[str, None] = Field(None, description="Слово, которое нужно добавить в словарь")
    part_of_speech: Union[str, None] = Field(None, description="Часть речи слова")
    translation: Union[str, None] = Field(None, description="Перевод слова")

    source: Optional[str] = Field(
        default="api", description="Источник запроса (api, bot, etc)"
    )

class UserMatchRequest(BaseModel):
    """
    Модель запроса на поиск собеседника.
    Содержит user_id и критерии поиска.
    """

    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    username: str = Field(..., description="Никнейм пользователя")
    criteria: Dict[str, str] = Field(..., description="Критерии поиска собеседника")
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now, description="Время создания запроса"
    )
    source: Optional[str] = Field(
        default="bot", description="Источник запроса (api, bot, etc)"
    )


class MatchCriteria(BaseModel):
    """
    Детализированная модель критериев поиска.
    Может использоваться вместо простого словаря для валидации.
    """

    language: Language = Field(default=Language.RU, description="Язык общения")
    topic: Topic = Field(default=Topic.GENERAL, description="Тема для общения")
    min_age: Optional[int] = Field(
        None, ge=18, le=100, description="Минимальный возраст собеседника"
    )
    max_age: Optional[int] = Field(
        None, ge=18, le=100, description="Максимальный возраст собеседника"
    )
    gender: Optional[str] = Field(None, description="Предпочтительный пол собеседника")


class UserMatchResponse(BaseModel):
    """
    Модель ответа после успешного добавления в очередь.
    """

    status: str = Field(..., description="Статус операции")
    user_id: int = Field(..., description="ID пользователя")
    queue_position: Optional[int] = Field(
        None, description="Позиция в очереди (если применимо)"
    )
    estimated_wait: Optional[int] = Field(
        None, description="Примерное время ожидания в секундах"
    )


class ChatSessionRequest(BaseModel):
    user_id: int = Field(..., description="ID первого пользователя")
    partner_id: int = Field(..., description="ID второго пользователя")
    room_id: str = Field(..., description="Уникальный ключ для комнаты")


class UserProfile(BaseModel):
    """
    Модель профиля пользователя (для базы данных).
    """

    user_id: str
    username: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    languages: List[Language]
    interests: List[Topic]
    created_at: datetime
    is_active: bool = True


class MatchFoundEvent(BaseModel):
    """
    Модель события найденного совпадения.
    Используется потребителем очереди для уведомления пользователей.
    """

    user_id_1: str
    user_id_2: str
    match_criteria: Dict[str, str]
    matched_at: datetime
    chat_room_id: str
