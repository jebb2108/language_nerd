__all__ = ("router",)

from aiogram import Router

from .commands import router as commands_router
from .callback_handlers import router as callback_handlers_router
# from .admin_commands import router as admin_commands_router
from .common import router as common_router

router = Router(name=__name__)

router.include_routers(
    callback_handlers_router,
    # admin_commands_router,
    commands_router,
)

# this has to be the last!
router.include_router(common_router)
