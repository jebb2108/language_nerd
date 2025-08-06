from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import Message, CallbackQuery
from config import Resources

class ResourcesMiddleware(BaseMiddleware):

    def __init__(self, resources: Resources):
        self.resources = resources

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Передаем resources в обработчики
        data["resources"] = self.resources
        return await handler(event, data)