"""Shared Pydantic models for user data.

Used by ALL teams. Do not modify without notifying other teams.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for creating a new user account."""

    model_config = ConfigDict(frozen=True)

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    # Allowed values: "trader", "journalist", "investor"
    persona_type: str = Field(..., description="trader, journalist, or investor")


class UserRead(BaseModel):
    """User data returned by the API (password excluded)."""

    model_config = ConfigDict(frozen=True)

    id: str
    username: str
    email: str
    # One of: "trader", "journalist", "investor"
    persona_type: str
    preferences: dict = Field(default_factory=dict)
    created_at: datetime
