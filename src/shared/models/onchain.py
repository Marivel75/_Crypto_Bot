"""On-chain data models for Bitcoin and Ethereum metrics.

Used by ETL team (src/etl/collectors/) to validate data from:
- Mempool.space (Bitcoin network stats)
- Blockchain.com (Bitcoin blockchain data)
- Etherscan (Ethereum gas tracker)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MempoolRecord(BaseModel):
    """Bitcoin mempool statistics from mempool.space."""

    model_config = ConfigDict(frozen=True)

    # Identifiers
    symbol: str = Field(default="BTC", description="Always BTC for mempool data")
    source: str = Field(default="mempool", description="Data source identifier")

    # Mempool stats
    unconfirmed_count: int = Field(..., ge=0, description="Unconfirmed transactions")
    total_fee_rate: Decimal = Field(..., ge=0, description="Average fee rate (sat/vB)")
    min_fee_rate: Decimal = Field(..., ge=0, description="Minimum fee rate (sat/vB)")
    max_fee_rate: Decimal = Field(..., ge=0, description="Maximum fee rate (sat/vB)")

    # Block info
    block_height: int = Field(..., ge=0, description="Current block height")
    block_timestamp: datetime = Field(..., description="Timestamp of latest block")
    blocks_expected: int = Field(default=6, ge=1, description="Expected blocks in time horizon")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When data was collected")

    class Config:
        """Pydantic config for frozen immutable records."""

        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class BlockchainBTCStats(BaseModel):
    """Bitcoin blockchain statistics from blockchain.com."""

    model_config = ConfigDict(frozen=True)

    # Identifiers
    symbol: str = Field(default="BTC", description="Always BTC")
    source: str = Field(default="blockchain.com", description="Data source identifier")

    # Network stats
    hashrate_tph: Decimal = Field(..., ge=0, description="Hashrate in terahashes per hour (TH/h)")
    difficulty: Decimal = Field(..., ge=0, description="Current difficulty")
    total_btc_supply: Decimal = Field(..., ge=0, description="Total BTC in circulation")

    # Transaction stats
    avg_transaction_size_bytes: int = Field(..., ge=0, description="Average transaction size (bytes)")
    mempool_transactions: int = Field(..., ge=0, description="Unconfirmed tx count")
    confirmed_transactions_24h: int = Field(..., ge=0, description="Transactions confirmed in 24h")

    # Fee estimate (in satoshis)
    fee_estimate_fast_sat: int = Field(..., ge=0, description="Fast fee (sat/byte)")
    fee_estimate_standard_sat: int = Field(..., ge=0, description="Standard fee (sat/byte)")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When data was collected")

    class Config:
        """Pydantic config for frozen immutable records."""

        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class EtherscanGasStats(BaseModel):
    """Ethereum gas tracker data from Etherscan."""

    model_config = ConfigDict(frozen=True)

    # Identifiers
    symbol: str = Field(default="ETH", description="Always ETH for gas stats")
    source: str = Field(default="etherscan", description="Data source identifier")

    # Gas prices (in Gwei)
    safe_gas_price_gwei: Decimal = Field(..., ge=0, description="Safe/low priority gas price (Gwei)")
    standard_gas_price_gwei: Decimal = Field(..., ge=0, description="Standard gas price (Gwei)")
    fast_gas_price_gwei: Decimal = Field(..., ge=0, description="Fast gas price (Gwei)")

    # Base fee (post-EIP-1559)
    base_fee_gwei: Decimal = Field(..., ge=0, description="Current base fee (Gwei)")

    # ETH/USD price for cost estimation
    eth_price_usd: Decimal = Field(..., ge=0, description="ETH/USD exchange rate")

    # Block info
    block_number: int = Field(..., ge=0, description="Current block number")
    block_timestamp: datetime = Field(..., description="Timestamp of latest block")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When data was collected")

    class Config:
        """Pydantic config for frozen immutable records."""

        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class CryptoRankCoin(BaseModel):
    """Market data for a coin from CryptoRank API."""

    model_config = ConfigDict(frozen=True)

    # Identifiers
    symbol: str = Field(..., description="Trading symbol, e.g. BTC, ETH")
    source: str = Field(default="cryptorank", description="Data source identifier")
    cryptorank_id: str = Field(..., description="Internal CryptoRank coin ID")

    # Rankings and metrics
    rank: int = Field(..., ge=1, description="Market cap rank")
    market_cap_usd: Decimal | None = Field(default=None, ge=0, description="Market cap in USD")
    price_usd: Decimal = Field(..., ge=0, description="Current price in USD")

    # 24h changes
    change_24h_percent: Decimal | None = Field(default=None, description="24h price change %")
    volume_24h_usd: Decimal | None = Field(default=None, ge=0, description="24h trading volume in USD")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When data was collected")

    class Config:
        """Pydantic config for frozen immutable records."""

        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}
