import os
from dataclasses import dataclass
from datetime import timezone, timedelta

from dotenv import load_dotenv

load_dotenv(".env")


@dataclass
class BotConfig:
    token: str = os.getenv("BOT_TOKEN")
    admin_id: int = os.getenv("ADMIN_ID")
    abs_img_path: str = os.getenv("ABS_IMG_PATH")

@dataclass
class GatewayConfig:
    host: str = os.getenv('GATEWAY_HOST')
    port: int = os.getenv('GATEWAY_PORT')

@dataclass
class RedisConfig:
    url: str = os.getenv("REDIS_URL")

@dataclass
class Config:

    debug = os.getenv("DEBUG")
    log_level = os.getenv("LOG_LEVEL")
    version = os.getenv("VERSION")
    tzinfo = timezone(timedelta(hours=3.0))

    bot: "BotConfig" = None
    gateway: "GatewayConfig" = None
    redis: "RedisConfig" = None

    def __post_init__(self):
        if not self.bot: self.bot = BotConfig()
        if not self.gateway: self.gateway = GatewayConfig()
        if not self.redis: self.redis = RedisConfig()


config = Config()