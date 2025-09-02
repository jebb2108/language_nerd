__all__ = ['router',]

from aiogram import Router
from ai_tasks_handler import router as ai_task_router

router = Router(name=__name__)
router.include_routers(
    ai_task_router,
)