import uvicorn
from fastapi import FastAPI
from config import config
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.matchmaking import router as match_router
from app.api.endpoints.websockets import router as websockets

from logging_config import opt_logger as log

logger = log.setup_logger("chat server")

# Создаем единственный экземпляр FastAPI
app = FastAPI()

origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
# и другие адреса, откуда может приходить фронтенд
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(match_router)
app.include_router(websockets)


if __name__ == "__main__":
    uvicorn.run(
        "app.chat_server:app",
        host="localhost",
        port=config.CHAT_SERVER_PORT,
        reload=True,
    )