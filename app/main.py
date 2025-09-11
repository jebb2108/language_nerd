from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.endpoints import router
from app.dependencies import get_rabbitmq, get_db, get_redis


@asynccontextmanager
async def startup(app: FastAPI):
    """Инициализация ресурсов"""
    await get_rabbitmq()
    await get_db()
    await get_redis()

    yield


app = FastAPI(lifespan=startup)
app.include_router(router)
