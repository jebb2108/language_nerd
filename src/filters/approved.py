from datetime import datetime
from typing import TYPE_CHECKING, Union

import httpx
from aiogram.fsm.context import FSMContext

from src.dependencies import get_gateway
from src.config import config
from src.logconf import opt_logger as log

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

logger = log.setup_logger("approved")


async def approved(callback: Union["CallbackQuery", "Message"], state: FSMContext = None):
    """Проверяет, не истекла ли подписка пользователя"""

    user_id = callback.from_user.id
    gateway = await get_gateway()

    async with gateway:
        # Отправляет запрос в GateWay -> dict[]
        response: "httpx.Response" = await gateway.get('due_to', user_id)
        # Получает тело ответа и статус код
        data, status_code = response.json(), response.status_code

        # Извлекает данные из ответа и конвертирует
        due_to = data.get('until') if data else None
        is_active = True if data and str(data.get('is_active', False)).lower() == 'true' else False

        # При передаче FSM обновляет состояние памяти с новым due_to
        if data and state: await state.update_data(due_to=due_to, is_active=is_active)

        # При подходящем статусе ответа выполняет проверки:
        if due_to and status_code == 200:
            # Переводит строку в объект datetime
            due_date = datetime.fromisoformat(due_to)
            # Приводим к naive datetime если нужно
            if due_date.tzinfo is not None:
                due_date = due_date.replace(tzinfo=None)

            # Наконец сверяет время пользователя из БД с текущим,
            # чтобы определить, может ли пользователь продолжать
            # пользоваться функциями бота
            if due_date > datetime.now(
                    tz=config.tzinfo
                ).replace(tzinfo=None):

                # Подтверждает, что
                # пользовательское время не просрочено
                return True

        return False