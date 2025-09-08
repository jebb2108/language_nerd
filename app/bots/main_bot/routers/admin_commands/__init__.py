__all__ = ("router",)

from aiogram import Router
from app.bots.main_bot.routers.admin_commands.tasks_handler import (
    router as admin_commands_router,
)

router = Router(name=__name__)
router.include_routers(
    admin_commands_router,
)
