__all__ = ['router', 'db_pool']

from aiogram import Router
from bots.middlewares.rate_limit_middleware import RateLimitMiddleware
from bots.middlewares.resources_middleware import ResourcesMiddleware

db_pool = None

router = Router(name=__name__)

# Инициализация middleware
resources_middleware = ResourcesMiddleware()

# Обработчики жизненного цикла
@router.startup()
async def on_startup_handler():
    global db_pool
    # Запуск веб-сервера
    db_pool = await resources_middleware.on_startup()

@router.shutdown()
async def on_shutdown_handler():
    await resources_middleware.on_shutdown()


# Регистрация middleware
router.message.middleware(resources_middleware)
router.callback_query.middleware(resources_middleware)
router.inline_query.middleware(resources_middleware)

router.message.middleware(RateLimitMiddleware())