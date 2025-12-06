from datetime import datetime, timedelta
from typing import Optional, List

from pydantic import BaseModel, Field

from src.config import config


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
    topics: List[str]
    lang_code: str


class NewPayment(BaseModel):
    """
    Модель платежа (для базы данных).
    """

    user_id: int = Field(..., description="User ID")
    amount: Optional[float] = Field(
        199.00, description="Amount of payment in rubles user agreed to pay"
    )
    period: Optional[str] = Field(
        "trial", description="Period of payment", examples=["month", "year"]
    )
    trial: Optional[bool] = Field(True, description="If it is trial period for user")
    untill: Optional[datetime] = (
        datetime.now(tz=config.bot.tzinfo) + timedelta(days=3)
    )
    currency: Optional[str] = Field("RUB", description="Currency of payment")