from pydantic import BaseModel, Field

from config import config


class SentMessage(BaseModel):
    chat_id = Field(..., description="Chat ID")
    message_id = Field(..., description="Message ID")
    text = Field(..., description="Message text")
    message_type: str = Field(default=config.DEFAULT_MESSAGE_TYPE, description="Message type")
