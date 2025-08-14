__all__ = ['router', ]

from aiogram import Router

from .registration_cb_handler import router as reg_cb_router
from .main_menu_cb_handler import router as main_menu_cb_router

router = Router(name=__name__)

router.include_routers(
    reg_cb_router,
    main_menu_cb_router,
)