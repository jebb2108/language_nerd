__all__ = ("router",)

from aiogram import Router
from .start_commands import router as start_commands_router
from .menu_commands import router as menu_commands_router
from .edit_profile_commands import router as edit_profile_commands_router

router = Router(name=__name__)

router.include_routers(
start_commands_router,
    menu_commands_router,
    edit_profile_commands_router
)
