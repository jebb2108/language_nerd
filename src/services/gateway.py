import httpx
from typing import Any, Optional

from src.config import config


class GatewayService:
    def __init__(self, host: str, port: int):
        self.gateway_url = f'http://{host}:{port}'
        self.session: Optional["httpx.AsyncClient"] = None

    async def __aenter__(self):
        self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    def connect(self, ) -> None:
        """Подключение к серверу"""
        self.session = httpx.AsyncClient()

    async def close(self) -> None:
        if self.session:
            await self.session.aclose()

    async def get(self, method_name: str, *args, **kwargs) -> Any:
        """ GET запросы к внешнему серверу """
        method = getattr(self, f"_get_{method_name}", None)

        if method is None:
            raise AttributeError(f'GET метод {method_name} не существует')

        return await method(*args, **kwargs)

    async def post(self, method_name: str, *args, **kwargs) -> Any:
        """POST запросы к внешнему серверу"""
        method = getattr(self, f"_post_{method_name}", None)

        if method is None:
            raise AttributeError(f'POST метод {method_name} не существует')

        return await method(*args, **kwargs)

    # GET функции
    async def _get_check_user_exists(self, user_id: int) -> httpx.Response:
        """Проверка существования пользователя"""
        url = f'{self.gateway_url}/user_exists?user_id={user_id}'
        response = await self.session.get(url=url)
        return response

    async def _get_due_to(self, user_id: int) -> httpx.Response:
        url = f'{self.gateway_url}/due_to?user_id={user_id}'
        response = await self.session.get(url=url)
        return response


gateway_service = GatewayService(config.gateway.host, config.gateway.port)


