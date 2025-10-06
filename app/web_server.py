import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.dependencies import get_db
from app.api.endpoints.dictionary import router as dict_router
from app.api.endpoints.yookassa import router as webhook_router
from config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация ресурсов"""
    await get_db()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(dict_router)
app.include_router(webhook_router)

if __name__ == "__main__":
    uvicorn.run(
        "app.web_server:app",
        host="localhost",
        port=config.WEB_SERVER_PORT,
        reload=True
    )
