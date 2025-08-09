__all__ = ['router']

from aiogram import Router
from rate_limit_middleware import RateLimitMiddleware
from resources_middleware import ResourcesMiddleware

router = Router(name=__name__)

# Инициализация middleware
resources_middleware = ResourcesMiddleware()

# Обработчики жизненного цикла
@router.startup()
async def on_startup_handler():
    await resources_middleware.on_startup()

@router.shutdown()
async def on_shutdown_handler():
    await resources_middleware.on_shutdown()


# Регистрация middleware
router.message.middleware(resources_middleware)
router.callback_query.middleware(resources_middleware)
router.inline_query.middleware(resources_middleware)

router.message.middleware(RateLimitMiddleware())