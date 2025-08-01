__all__ = ('router',)

from aiogram import Router

from .start_commands import router as start_commands_router
from .menu_commands import router as menu_commands_router
from .partner_commands import router as partner_commands_router
from .weekly_message_commands import router as weekly_message_commands_router

router = Router()

router.include_routers(
    start_commands_router,
    menu_commands_router,
    partner_commands_router,
    weekly_message_commands_router,
)
