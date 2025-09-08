__all__ = ("router",)

from aiogram import Router
from .partner_commands import (
    router as partner_commands_router,
)

router = Router(name=__name__)

router.include_routers(
    partner_commands_router,
)
