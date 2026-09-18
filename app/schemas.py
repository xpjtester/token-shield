from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: Any
    name: str | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = None
    messages: list[Message]
    stream: bool = False
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    temperature: float | None = None
    user: str | None = None
    token_shield: dict[str, Any] = Field(default_factory=dict)


class ContextOptimizeRequest(BaseModel):
    context: str = Field(min_length=1)
    mode: Literal["safe", "balanced"] = "balanced"


class TokenStatsRequest(BaseModel):
    text: str
    optimized_text: str | None = None
