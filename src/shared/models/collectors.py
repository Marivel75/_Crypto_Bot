"""Pydantic models for new collector data."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OnChainMetric(BaseModel):
    """On-chain metric from blockchain or Etherscan."""

    id: UUID | None = None
    symbol: Literal["BTC", "ETH"]
    metric_type: Literal[
        "WHALE_TRANSACTION",
        "NETWORK_ACTIVE",
        "MINER_REVENUE",
        "GAS_PRICE",
        "BURN_RATE",
        "STAKING_RATIO",
    ]
    metric_value: Decimal = Field(..., decimal_places=8)
    metric_unit: str = Field(..., max_length=50)
    source: str = Field(..., max_length=100)
    collected_at: datetime | None = None

    model_config = {"from_attributes": True}


class RegulatoryAlert(BaseModel):
    """Regulatory alert from ESMA, SEC, or other authority."""

    id: UUID | None = None
    title: str = Field(..., max_length=500)
    content: str
    source: Literal["ESMA", "SEC", "EU_BLOCKCHAIN"]
    jurisdiction: str | None = Field(None, max_length=50)
    impact_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None
    url: str | None = Field(None, max_length=1000)
    published_at: datetime | None = None
    collected_at: datetime | None = None

    model_config = {"from_attributes": True}


class BlockchainMetric(BaseModel):
    """Generic blockchain metric for on-chain data collection."""

    symbol: Literal["BTC", "ETH"]
    metric_type: str
    metric_value: float
    metric_unit: str
    timestamp: datetime


class EtherscanGasPrice(BaseModel):
    """Etherscan gas price data."""

    safe_gas_price: str
    standard_gas_price: str
    fast_gas_price: str
    suggest_base_fee: str
    timestamp: datetime | None = None


class EtherscanNetworkStats(BaseModel):
    """Etherscan network statistics."""

    eth_price_usd: str | None = None
    transaction_count_24h: str | None = None
    active_address_count_24h: str | None = None
    network_utilization: str | None = None
    timestamp: datetime | None = None
