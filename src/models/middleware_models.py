from pydantic import BaseModel, Field

class SentMessage(BaseModel):
    chat_id: int = Field(..., description="Chat ID")
    message_id: int = Field(..., description="Message ID")
    text: str = Field(..., description="Message text")