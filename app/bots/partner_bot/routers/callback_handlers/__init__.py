__all__ = ("router",)

from aiogram import Router
from .partner_cb_handler import (
    router as partner_cb_handler_router,
)

router = Router(name=__name__)

router.include_routers(
    partner_cb_handler_router,
)
