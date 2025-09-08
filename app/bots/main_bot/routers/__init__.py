__all__ = ("router",)

from aiogram import Router

# даем команду питону экспортировать переменную router
__all__ = ("router",)

from aiogram import Router
from app.bots.main_bot.routers.admin_commands import router as admin_commands_router
from app.bots.main_bot.routers.callback_handlers import (
    router as callback_handlers_router,
)
from app.bots.main_bot.routers.commands import router as commands_router
from app.bots.main_bot.routers.common import router as common_router

router = Router(name=__name__)

router.include_routers(
    callback_handlers_router,
    commands_router,
)

# this has to be the last!
router.include_router(common_router)
