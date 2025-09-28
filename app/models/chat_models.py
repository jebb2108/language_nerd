from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

from app.models import Language, Topic


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
    user_id: int = Field(..., description="ID первого пользователя")
    partner_id: int = Field(..., description="ID второго пользователя")
    room_id: str = Field(..., description="Уникальный ключ для комнаты")


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
