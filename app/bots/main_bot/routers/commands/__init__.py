__all__ = ("router",)

from aiogram import Router
from app.bots.main_bot.routers.commands.menu_commands import (
    router as menu_commands_router,
)
from app.bots.main_bot.routers.commands.start_commands import (
    router as start_commands_router,
)

router = Router(name=__name__)

router.include_routers(
    menu_commands_router,
    start_commands_router,
)
