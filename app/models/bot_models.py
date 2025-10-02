from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

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
    Модель профиля пользователя (для базы данных).
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
    untill: Optional[str] = (
        datetime.now(tz=config.TZINFO) + timedelta(days=3)
    ).isoformat()
    currency: Optional[str] = Field("RUB", description="Currency of payment")
