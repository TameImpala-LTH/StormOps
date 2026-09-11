"""Pydantic schemas for personal conversation history and messages."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageItem(BaseModel):
    """Single message item in a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str = Field(..., description="'user' | 'assistant'")
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """Concise conversation summary for personal weather timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    location_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_query: Optional[str] = None
    last_answer: Optional[str] = None


class ConversationDetail(BaseModel):
    """Full conversation with message items."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    location_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageItem] = Field(default_factory=list)
