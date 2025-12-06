from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Union

import httpx
from aiogram.fsm.context import FSMContext

from src.dependencies import get_gateway
from src.utils.access_data import data_storage
from src.config import config
from src.logconf import opt_logger as log

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

logger = log.setup_logger("paytime")


async def approved(callback: Union["CallbackQuery", "Message"], state: FSMContext = None):
    """Проверяет, не истекла ли подписка пользователя"""
    user_id = callback.from_user.id

    # 1. Проверяем кэш в gateway
    gateway = await get_gateway()
    async with gateway:
        response = await gateway.get('due_to', user_id)
        due_to = response.json()
        if state: await state.update_data(due_to=due_to)
        if due_to:
            due_date = datetime.fromisoformat(due_to)
            # Приводим к naive datetime если нужно
            if due_date.tzinfo is not None:
                due_date = due_date.replace(tzinfo=None)

            if due_date > datetime.now().replace(tzinfo=None):
                return True

    # 2. Отправляем запрос для получения платежного статуса
    async with gateway:
        data = await gateway.get('due_to', user_id)
        due_to, is_active = data['due_to'], data['is_active']
        native_db_dueto = due_to.replace(tzinfo=None) if due_to else None
        # Дата и время в базе данных больше текущего
        if native_db_dueto and \
                native_db_dueto > datetime.now().astimezone(tz=config.TZINFO).replace(tzinfo=None):
            # Приводим к naive datetime
            if is_active:
                # Сохраняем в кэш как ISO строку без временной зоны
                await gateway.post(
                    'due_to',
                    user_id, True
                )

            return True

        return False