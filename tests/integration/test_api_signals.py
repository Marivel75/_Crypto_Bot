"""Integration tests for /api/v1/signals endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

_ACTIVE_URL = "/api/v1/signals/active"
_PERFORMANCE_URL = "/api/v1/signals/performance"

_FIXED_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers — seed DB with test signal data
# ---------------------------------------------------------------------------


async def _seed_signal(
    db_session: AsyncSession,
    symbol: str = "BTCUSDT",
    signal_type: str = "BUY",
    confidence: float = 0.80,
    created_at: datetime | None = None,
) -> object:
    from src.shared.models.orm import TradingSignalOrm

    ts = created_at or _FIXED_TS
    signal = TradingSignalOrm(
        symbol=symbol,
        signal_type=signal_type,
        confidence_score=confidence,
        timeframe_primary="4h",
        timeframes_aligned={},
        rules_triggered=["rsi_oversold_multi_tf"],
        leverage_suggested=None,
        margin_safety=None,
        fees_estimated=None,
        model_version="rules_v1",
        created_at=ts,
    )
    db_session.add(signal)
    await db_session.commit()
    await db_session.refresh(signal)
    return signal


# ---------------------------------------------------------------------------
# GET /api/v1/signals/active
# ---------------------------------------------------------------------------


class TestActiveSignalsEndpoint:
    @pytest.mark.asyncio
    async def test_active_returns_200(self, client: AsyncClient) -> None:
        response = await client.get(_ACTIVE_URL)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_active_returns_list_in_data(self, client: AsyncClient) -> None:
        response = await client.get(_ACTIVE_URL)
        body = response.json()
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_active_empty_when_no_signals(self, client: AsyncClient) -> None:
        response = await client.get(_ACTIVE_URL)
        body = response.json()
        # No signals seeded, so the list should be empty (last 24h filter)
        assert body["data"] == []

    @pytest.mark.asyncio
    async def test_active_returns_recently_seeded_signal(self, client: AsyncClient, db_session: AsyncSession) -> None:
        # Signal created very recently (now) → should appear in active
        recent_ts = datetime.now(tz=UTC)
        await _seed_signal(db_session, created_at=recent_ts)

        response = await client.get(_ACTIVE_URL)
        body = response.json()
        assert len(body["data"]) >= 1

    @pytest.mark.asyncio
    async def test_active_signal_has_required_fields(self, client: AsyncClient, db_session: AsyncSession) -> None:

        recent_ts = datetime.now(tz=UTC)
        await _seed_signal(db_session, created_at=recent_ts)

        response = await client.get(_ACTIVE_URL)
        body = response.json()
        assert len(body["data"]) >= 1
        signal = body["data"][0]
        required = {"id", "symbol", "signal_type", "confidence_score", "timeframe_primary", "model_version"}
        assert required <= set(signal.keys())

    @pytest.mark.asyncio
    async def test_active_signal_type_is_buy_or_sell(self, client: AsyncClient, db_session: AsyncSession) -> None:

        recent_ts = datetime.now(tz=UTC)
        await _seed_signal(db_session, signal_type="BUY", created_at=recent_ts)

        response = await client.get(_ACTIVE_URL)
        body = response.json()
        for signal in body["data"]:
            assert signal["signal_type"] in {"BUY", "SELL", "HOLD"}


# ---------------------------------------------------------------------------
# GET /api/v1/signals/performance
# ---------------------------------------------------------------------------


class TestSignalPerformanceEndpoint:
    @pytest.mark.asyncio
    async def test_performance_returns_200(self, client: AsyncClient) -> None:
        response = await client.get(_PERFORMANCE_URL)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_performance_has_expected_fields(self, client: AsyncClient) -> None:
        response = await client.get(_PERFORMANCE_URL)
        body = response.json()
        data = body["data"]
        assert "total_signals" in data
        assert "evaluated_signals" in data
        assert "correct_signals" in data
        assert "win_rate" in data

    @pytest.mark.asyncio
    async def test_performance_total_signals_zero_initially(self, client: AsyncClient) -> None:
        response = await client.get(_PERFORMANCE_URL)
        body = response.json()
        assert body["data"]["total_signals"] == 0

    @pytest.mark.asyncio
    async def test_performance_total_increments_after_seed(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_signal(db_session, symbol="BTCUSDT")
        await _seed_signal(db_session, symbol="ETHUSDT")

        response = await client.get(_PERFORMANCE_URL)
        body = response.json()
        assert body["data"]["total_signals"] == 2

    @pytest.mark.asyncio
    async def test_performance_win_rate_none_when_no_outcomes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _seed_signal(db_session)

        response = await client.get(_PERFORMANCE_URL)
        body = response.json()
        # No outcomes seeded → win_rate should be None
        assert body["data"]["win_rate"] is None
