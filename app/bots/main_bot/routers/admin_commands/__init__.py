__all__ = ("router",)

from aiogram import Router
from .send_pending_handler import router as admin_commands_router

router = Router(name=__name__)
router.include_routers(
    admin_commands_router,
)
