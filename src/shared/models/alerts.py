"""Pydantic models for alert system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AlertRuleCreate(BaseModel):
    """Input model for creating an alert rule."""

    rule_name: str = Field(..., min_length=1, max_length=100)
    rule_type: Literal["SIGNAL", "PRICE", "NEWS", "PORTFOLIO", "CUSTOM"]
    condition: dict[str, Any] = Field(...)
    enabled: bool = Field(default=True)
    channels: list[Literal["email", "telegram", "in_app"]] = Field(
        default=["email"],
        min_length=1,
        max_length=3,
    )

    @field_validator("rule_name")
    @classmethod
    def validate_rule_name(cls, v: str) -> str:
        """Validate rule name is not empty."""
        if not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip()

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate condition is not empty."""
        if not v:
            raise ValueError("Condition cannot be empty")
        return v


class AlertRuleRead(BaseModel):
    """Response model for alert rule."""

    id: UUID
    user_id: UUID
    rule_name: str
    rule_type: Literal["SIGNAL", "PRICE", "NEWS", "PORTFOLIO", "CUSTOM"]
    condition: dict[str, Any]
    enabled: bool
    channels: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleUpdate(BaseModel):
    """Input model for updating an alert rule."""

    rule_name: str | None = None
    condition: dict[str, Any] | None = None
    enabled: bool | None = None
    channels: list[Literal["email", "telegram", "in_app"]] | None = None

    @field_validator("rule_name")
    @classmethod
    def validate_rule_name(cls, v: str | None) -> str | None:
        """Validate rule name if provided."""
        if v is not None and not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip() if v else None

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate condition if provided."""
        if v is not None and not v:
            raise ValueError("Condition cannot be empty")
        return v


class AlertHistoryRead(BaseModel):
    """Response model for alert history entry."""

    id: UUID
    alert_rule_id: UUID
    user_id: UUID
    trigger_event: dict[str, Any]
    alert_content: str
    channels_sent: list[str]
    sent_at: datetime
    status: Literal["SENT", "FAILED", "BOUNCED"]
    error_message: str | None

    model_config = {"from_attributes": True}


class AlertEvent(BaseModel):
    """Event that triggers alert evaluation."""

    event_type: Literal["SIGNAL", "PRICE", "NEWS", "PORTFOLIO"]
    data: dict[str, Any]
    timestamp: datetime
