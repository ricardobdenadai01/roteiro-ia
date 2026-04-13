from pydantic import BaseModel


class Message(BaseModel):
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    history: list[Message] = []


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    campaigns_used: list[str] = []
