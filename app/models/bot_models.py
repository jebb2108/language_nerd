from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from config import config


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


class NewUser(BaseModel):
    """
    Модель нового пользователя (для базы данных).
    """

    user_id: int
    username: Optional[str]
    camefrom: str
    first_name: str
    language: str
    fluency: int
    topic: str
    lang_code: str


class NewPayment(BaseModel):
    """
    Модель платежа (для базы данных).
    """

    user_id: int = Field(..., description="User ID")
    amount: Optional[int] = Field(
        199, description="Amount of payment in rubles user agreed to pay"
    )
    period: Optional[str] = Field(
        "trial", description="Period of payment", examples=["month", "year"]
    )
    trial: Optional[bool] = Field(True, description="If it is trial period for user")
    untill: Optional[datetime] = (
        datetime.now(tz=config.TZINFO) + timedelta(days=3)
    )
    currency: Optional[str] = Field("RUB", description="Currency of payment")


class UserProfile(BaseModel):
    """
    Модель профиля пользователя (для базы данных)
    """
    user_id: int = Field(..., description="User ID")
    nickname: str = Field(..., description="Уникальный никнейм пользователя")
    birthday: str = Field(..., description="Дата рождения пользователя (ISO)")
    about: str = Field(..., description="Краткая информация о пользователе")
    dating: Optional[bool] = Field(False, description="Согласие на дэйтинг")
    gender: Optional[str] = Field("unknown", description="Пол пользователя")
    is_active: Optional[bool] = Field(True, description="Активность пользователя")
    status: Optional[str] = Field("rookie", description="Статус пользователя")


class Location(BaseModel):
    """
    Модель местоположения пользователя (для базы данных)
    """
    user_id: int = Field(..., description="User ID")
    latitude: Optional[str] = Field(None, description="Долгота координаты")
    longitude: Optional[str] = Field(None, description="Широта координаты")
    city: Optional[str] = Field(None, description="Город пользователя")
    country: Optional[str] = Field(None, description="Страна пользователя")
    tzone: Optional[str] = Field(None, description="Временная зона пользователя")


