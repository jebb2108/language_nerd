__all__ = ("router",)

from aiogram import Router
from .callback_handlers import (
    router as partner_cb_handler_router,
)
from .commands import router as partner_commands_router

from .common import router as common_router

router = Router(name=__name__)

router.include_routers(
    partner_cb_handler_router,
    partner_commands_router,
)

router.include_router(common_router)
