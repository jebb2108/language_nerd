import re
from datetime import datetime
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator

from app.models import Language, Topic
from config import config


class Coordinates(BaseModel):
    """
    Модель первичной обработки геолокации пользователя
    """
    latitude: float
    longitude: float


class RegistrationData(BaseModel):
    """
    Модель профиля пользователя (для базы данных)
    """
    user_id: int = Field(..., description="User ID")
    nickname: str = Field(..., description="Уникальный никнейм пользователя")
    email: str = Field(..., description="Email пользователя")
    birthday: str = Field(..., description="Дата рождения пользователя (ISO)")
    gender: str = Field(..., description="Пол пользователя")
    about: str = Field(..., description="Краткая информация о пользователе")
    dating: Optional[bool] = Field(None, description="Согласие на дэйтинг")
    location: Optional[Coordinates] = None


class MessageContent(BaseModel):
    """
    Модель содержимого сообщения
    """
    sender: str = Field(..., description="Никнейм пользователя. Не путать с username!")
    text: str = Field(..., description="Слова, которое нужно проверить на статус выученного")
    created_at: str = Field(..., description="Время создания сообщения ISO формата")
    room_id: str = Field(..., description="Комната сессии, где слово было использовано")


class WebMatchToggleRequest(BaseModel):
    """Упрощенная модель для переключения состояния очереди через веб-интерфейс"""
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    action: str = Field(..., description="Действие: 'join' или 'leave'")


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
    """Модель ответа с данными пользователя для матчинга"""
    user_id: int
    username: str
    criteria: Dict[str, Any]
    gender: str
    lang_code: str
    status: str
    source: str = "web"


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


