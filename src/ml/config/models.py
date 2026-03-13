"""Pydantic models for indicator configuration (A4 — Architecture task)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RSIConfig(BaseModel):
    """RSI (Relative Strength Index) indicator configuration."""

    period: int = Field(default=14, ge=2, le=100)
    overbought: int = Field(default=70, ge=50, le=100)
    oversold: int = Field(default=30, ge=0, le=50)
    timeframes: list[str] = Field(default_factory=lambda: ["1h", "2h", "3h", "4h"])
    convergence_threshold: float = Field(default=5.0, ge=0.0, le=100.0)
    convergence_window: int = Field(default=3, ge=1, le=10)

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes(cls, v: list[str]) -> list[str]:
        """Ensure timeframes are non-empty."""
        if not v:
            raise ValueError("timeframes must not be empty")
        return v

    @field_validator("overbought")
    @classmethod
    def validate_overbought_oversold(cls, v: int, info) -> int:
        """Ensure overbought > oversold."""
        if "oversold" in info.data and v <= info.data["oversold"]:
            raise ValueError("overbought must be greater than oversold")
        return v


class BollingerConfig(BaseModel):
    """Bollinger Bands indicator configuration."""

    period: int = Field(default=20, ge=2, le=200)
    std_dev: float = Field(default=2.0, ge=0.5, le=5.0)
    squeeze_threshold: float = Field(default=0.02, ge=0.0, le=1.0)
    squeeze_width: float = Field(default=0.02, ge=0.0, le=1.0)
    timeframes: list[str] = Field(default_factory=lambda: ["1h", "2h", "3h", "4h", "1D"])

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes(cls, v: list[str]) -> list[str]:
        """Ensure timeframes are non-empty."""
        if not v:
            raise ValueError("timeframes must not be empty")
        return v


class HarmonicPatternConfig(BaseModel):
    """Configuration for a single harmonic pattern (gartley, butterfly, bat, crab)."""

    xb: float = Field(ge=0.0, le=1.0)
    ac: list[float] = Field(min_length=2, max_length=2)
    bd: list[float] = Field(min_length=2, max_length=2)
    xd: float | list[float] = Field()


class HarmonicConfig(BaseModel):
    """Harmonic patterns indicator configuration."""

    patterns: dict[str, HarmonicPatternConfig] = Field(
        default_factory=lambda: {
            "gartley": HarmonicPatternConfig(xb=0.618, ac=[0.382, 0.886], bd=[1.272, 1.618], xd=0.786),
            "butterfly": HarmonicPatternConfig(xb=0.786, ac=[0.382, 0.886], bd=[1.618, 2.618], xd=[1.272, 1.618]),
            "bat": HarmonicPatternConfig(xb=[0.382, 0.5], ac=[0.382, 0.886], bd=[1.618, 2.618], xd=0.886),
            "crab": HarmonicPatternConfig(xb=[0.382, 0.618], ac=[0.382, 0.886], bd=[2.618, 3.618], xd=1.618),
        }
    )
    tolerance: float = Field(default=0.05, ge=0.0, le=0.5)
    timeframes: list[str] = Field(default_factory=lambda: ["4h", "1D"])


class TrendConfig(BaseModel):
    """Trend analysis indicator configuration."""

    short_window: int = Field(default=20, ge=2, le=50)
    long_window: int = Field(default=50, ge=20, le=200)
    weekly_period: int = Field(default=7, ge=1, le=30)
    monthly_period: int = Field(default=30, ge=7, le=90)
    slope_threshold: float = Field(default=0.001, ge=0.0, le=0.1)
    dip_threshold: float = Field(default=-0.03, le=0.0)
    weekly: dict[str, Any] = Field(default_factory=lambda: {"type": "stable", "slope_threshold": 0.001})
    monthly: dict[str, Any] = Field(default_factory=lambda: {"type": "aggressive", "slope_threshold": 0.005})
    timeframes: list[str] = Field(default_factory=lambda: ["1D", "1W", "1M"])


class MultiTimeframeConfig(BaseModel):
    """Multi-timeframe signal aggregation configuration."""

    timeframes: list[str] = Field(default_factory=lambda: ["1h", "2h", "3h", "4h"])
    majority_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    supermajority_threshold: float = Field(default=1.0, ge=0.5, le=1.0)


class LeverageConfig(BaseModel):
    """Leverage and margin safety configuration."""

    max_leverage: int = Field(default=20, ge=1, le=100)
    margin_safety_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)


class FeeConfig(BaseModel):
    """Trading fee configuration."""

    maker: float = Field(default=0.001, ge=0.0, le=0.1)
    taker: float = Field(default=0.001, ge=0.0, le=0.1)
    funding_rate: float = Field(default=0.0001, ge=0.0, le=0.01)


class ConfidenceConfig(BaseModel):
    """Signal confidence threshold configuration."""

    min_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    high_threshold: float = Field(default=0.8, ge=0.5, le=1.0)

    @field_validator("high_threshold")
    @classmethod
    def validate_high_vs_min(cls, v: float, info) -> float:
        """Ensure high_threshold >= min_threshold."""
        if "min_threshold" in info.data and v < info.data["min_threshold"]:
            raise ValueError("high_threshold must be >= min_threshold")
        return v


class IndicatorConfig(BaseModel):
    """Complete indicator configuration (root model)."""

    rsi: RSIConfig = Field(default_factory=RSIConfig)
    bollinger: BollingerConfig = Field(default_factory=BollingerConfig)
    harmonic: HarmonicConfig = Field(default_factory=HarmonicConfig)
    trend: TrendConfig = Field(default_factory=TrendConfig)
    multi_tf: MultiTimeframeConfig = Field(default_factory=MultiTimeframeConfig)
    leverage: LeverageConfig = Field(default_factory=LeverageConfig)
    fees: FeeConfig = Field(default_factory=FeeConfig)
    confidence: ConfidenceConfig = Field(default_factory=ConfidenceConfig)

    class Config:
        """Pydantic v2 config."""

        frozen = True  # immutable config

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> IndicatorConfig:
        """Construct from a loaded YAML dict with lenient validation.

        Args:
            config_dict: Parsed YAML dict (from indicators.yaml).

        Returns:
            Validated IndicatorConfig instance.
        """
        return cls(**config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Export to dict (for compatibility with existing code)."""
        return self.model_dump(mode="python")
