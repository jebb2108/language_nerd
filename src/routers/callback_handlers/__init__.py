__all__ = ("router",)

from aiogram import Router
from .main_menu_cb_handler import router as main_menu_cb_handler_router
from .registration_cb_handler import router as registration_cb_handler_router
# from .quiz_cb_handler import router as weekly_message_cb_handler_router
from .payment_cb_handler import router as payment_cb_handler_router
from .change_profile_cb_handler import router as change_profile_cb_handler_router

router = Router(name=__name__)

router.include_routers(
    main_menu_cb_handler_router,
    change_profile_cb_handler_router,
    registration_cb_handler_router,
    # weekly_message_cb_handler_router,
)

# this has to be the last one
router.include_router(payment_cb_handler_router)
