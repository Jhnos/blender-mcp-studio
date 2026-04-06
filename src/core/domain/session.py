"""Session entity — tracks a user conversation session."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in the conversation."""

    model_config = {"frozen": True}

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """Entity tracking a single user conversation. Immutable — use add_message() to evolve."""

    model_config = {"frozen": True}

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = Field(default_factory=list)
    workflow: str = "conversational_modeling"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, role: str, content: str) -> Session:
        msg = Message(role=role, content=content)
        return self.model_copy(update={"messages": [*self.messages, msg]})

    def last_user_message(self) -> str | None:
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None
