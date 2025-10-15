from typing import List, Any, Optional

from pydantic import BaseModel


class QuestionData(BaseModel):

    word: str
    sentence: str
    options: List[str]
    correct_index: int


class UserWords(BaseModel):
    """Модель пользователя и его слов"""

    user_id: int
    words: List[str]


class ReportData(BaseModel):
    """Модель данных для отчета"""

    word: str
    sentence: str
    options: List[str]
    correct_index: int


class UserReport(BaseModel):
    """Данные отчета пользователя"""

    report_id: int
    user_id: int
    words: List[dict[str, Any]]
    user_info: dict[str, Any]


class PendingReport(BaseModel):
    """Ожидающий отправки отчет"""

    report_id: int
    user_id: int


class DeliveryResult(BaseModel):
    """Результат отправки отчета"""

    success: bool
    report_id: int
    user_id: int
    error_type: Optional[str] = None
    error_message: Optional[str] = None

