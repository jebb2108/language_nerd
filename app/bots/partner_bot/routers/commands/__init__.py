__all__ = ("router",)

from aiogram import Router
from .registration_commands import router as registration_commands_router
from .partner_commands import router as partner_commands_router

router = Router(name=__name__)

router.include_routers(
    registration_commands_router,
    partner_commands_router,
)
