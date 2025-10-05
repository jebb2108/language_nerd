from datetime import datetime
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field

from app.models import Language, Topic
from config import config


class MessageContent(BaseModel):
    """
    Модель содержимого сообщения
    """
    sender: str = Field(..., description="Никнейм пользователя. Не путать с username!")
    message: dict = Field(..., description="Слова, которое нужно проверить на статус выученного")
    created_at: str = Field(..., description="Время создания сообщения ISO формата")
    room_id: str = Field(..., description="Комната сессии, где слово было использовано")


class UserMatchRequest(BaseModel):
    """
    Модель запроса на поиск собеседника
    """
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    username: str = Field(..., description="Никнейм пользователя")
    criteria: Dict[str, Any] = Field(..., description="Критерии поиска собеседника")
    gender: str = Field(..., description="Пол пользователя")
    lang_code: str = Field(..., description="Код языка пользователя")
    status: str = Field(default=config.SEARCH_STARTED, description="Статус запроса")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(tz=config.TZINFO).isoformat(),
        description="Время создания запроса"
    )
    current_time: Optional[str] = Field(
        default_factory=lambda: datetime.now(tz=config.TZINFO).isoformat(),
        description="Время создания запроса"
    )
    source: Optional[str] = Field(
        default="bot", description="Источник запроса (api, bot, etc)"
    )


class UserMatchResponse(BaseModel):
    """
    Модель ответа после успешного добавления в очередь.
    """

    status: str = Field(..., description="Статус операции")
    user_id: int = Field(..., description="ID пользователя")
    lang_code: str = Field(..., description="Код языка пользователя")
    queue_position: Optional[int] = Field(
        None, description="Позиция в очереди (если применимо)"
    )
    estimated_wait: Optional[int] = Field(
        None, description="Примерное время ожидания в секундах"
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


class ChatSessionRequest(BaseModel):
    room_id: str = Field(..., description="Уникальный ключ для комнаты")
    user_id: int = Field(..., description="ID первого пользователя")
    partner_id: int = Field(..., description="ID второго пользователя")
    matched_at: str = Field(..., description="Время создания пары")


class MatchFoundEvent(BaseModel):
    """
    Модель события найденного совпадения.
    Используется потребителем очереди для уведомления пользователей.
    """
    user_id: int = Field(..., description="User ID участника")
    username: str = Field(..., description="Username участника")
    gender: str = Field(..., description="Пол участника")
    lang_code: str = Field(..., description="Языковой код участника")
    match_criteria: Dict[str, str] = Field(..., description="Критерии найденной пары")


