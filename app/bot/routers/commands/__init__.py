__all__ = ("router",)

from aiogram import Router
from .start_commands import router as start_commands_router
from .menu_commands import router as menu_commands_router

router = Router(name=__name__)

router.include_routers(
start_commands_router,
    menu_commands_router,
)
