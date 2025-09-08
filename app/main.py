from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.rabbitmq import rabbitmq_service
from app.services.database import database_service
from app.services.redis import redis_service
from app.api.endpoints import router as api_router

# from app.bot.handlers import router as bot_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await rabbitmq_service.connect()
    await database_service.connect()
    await redis_service.connect()

    # Запуск бота (если нужно)
    # asyncio.create_task(bot_router.start_polling())

    yield

    # Shutdown
    await rabbitmq_service.disconnect()
    await database_service.disconnect()
    await redis_service.disconnect()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api")
