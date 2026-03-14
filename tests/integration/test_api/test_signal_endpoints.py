"""Integration tests for signal endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.orm import SignalOutcomeOrm, TradingSignalOrm

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seed_signals(db_session: AsyncSession) -> list[TradingSignalOrm]:
    """Insert sample trading signals and return them."""
    signals: list[TradingSignalOrm] = []
    for i in range(3):
        signal = TradingSignalOrm(
            symbol="BTCUSDT",
            signal_type="BUY" if i % 2 == 0 else "SELL",
            confidence_score=0.7 + i * 0.05,
            timeframe_primary="4h",
            timeframes_aligned={"1h": {"rsi": 25 + i}, "4h": {"rsi": 28 + i}},
            rules_triggered=["rsi_oversold_multi_tf"],
            leverage_suggested=5,
            margin_safety=2.0,
            fees_estimated=0.002,
            model_version="rules_v1",
        )
        db_session.add(signal)
        signals.append(signal)
    await db_session.commit()
    for s in signals:
        await db_session.refresh(s)
    return signals


@pytest.fixture
async def seed_signal_with_outcome(
    db_session: AsyncSession,
) -> tuple[TradingSignalOrm, SignalOutcomeOrm]:
    """Insert a single signal with an associated outcome."""
    signal = TradingSignalOrm(
        symbol="ETHUSDT",
        signal_type="BUY",
        confidence_score=0.85,
        timeframe_primary="1h",
        timeframes_aligned={"1h": {"rsi": 30}, "4h": {"rsi": 32}},
        rules_triggered=["rsi_oversold_multi_tf", "bollinger_squeeze"],
        leverage_suggested=3,
        margin_safety=2.5,
        fees_estimated=0.001,
        model_version="rules_v1",
    )
    db_session.add(signal)
    await db_session.flush()
    await db_session.refresh(signal)

    outcome = SignalOutcomeOrm(
        signal_id=signal.id,
        price_at_signal=3000.0,
        price_after_1h=3050.0,
        price_after_4h=3100.0,
        price_after_1d=3200.0,
        pnl_simulated=6.67,
        was_correct=True,
        evaluated_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    db_session.add(outcome)
    await db_session.commit()
    await db_session.refresh(signal)
    await db_session.refresh(outcome)
    return signal, outcome


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSignalEndpoints:
    # --- /active ---

    @pytest.mark.asyncio
    async def test_get_active_signals_empty(self, client: AsyncClient) -> None:
        """GET /active returns an empty list when no signals exist."""
        resp = await client.get("/api/v1/signals/active")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["error"] is None

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_signals")
    async def test_get_active_signals_with_data(self, client: AsyncClient) -> None:
        """GET /active returns all signals created in the last 24 h."""
        resp = await client.get("/api/v1/signals/active")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        # Each item must carry expected fields
        first = data[0]
        assert "id" in first
        assert "symbol" in first
        assert "signal_type" in first
        assert "confidence_score" in first
        assert first["symbol"] == "BTCUSDT"

    # --- /{symbol} ---

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_signals")
    async def test_get_signal_by_symbol(self, client: AsyncClient) -> None:
        """GET /{symbol} returns paginated signals for a given symbol."""
        resp = await client.get("/api/v1/signals/BTCUSDT")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        meta = body["meta"]
        assert len(data) == 3
        assert all(s["symbol"] == "BTCUSDT" for s in data)
        assert meta["total"] == 3
        assert meta["page"] == 1

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_signals")
    async def test_get_signal_by_symbol_with_timeframe_filter(self, client: AsyncClient) -> None:
        """GET /{symbol}?timeframe=4h returns only signals matching that timeframe."""
        resp = await client.get("/api/v1/signals/BTCUSDT?timeframe=4h")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        assert all(s["timeframe_primary"] == "4h" for s in data)

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_signals")
    async def test_get_signal_by_symbol_no_match_for_timeframe(self, client: AsyncClient) -> None:
        """GET /{symbol}?timeframe=1d returns empty when no signals on that timeframe."""
        resp = await client.get("/api/v1/signals/BTCUSDT?timeframe=1d")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("seed_signals")
    async def test_get_signal_by_symbol_pagination(self, client: AsyncClient) -> None:
        """GET /{symbol}?limit=2&page=1 returns at most 2 items."""
        resp = await client.get("/api/v1/signals/BTCUSDT?limit=2&page=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 3
        assert body["meta"]["limit"] == 2

    # --- /{signal_id}/detail ---

    @pytest.mark.asyncio
    async def test_get_signal_detail(
        self,
        client: AsyncClient,
        seed_signal_with_outcome: tuple[TradingSignalOrm, SignalOutcomeOrm],
    ) -> None:
        """GET /{signal_id}/detail returns signal with its outcome."""
        signal, outcome = seed_signal_with_outcome
        resp = await client.get(f"/api/v1/signals/{signal.id}/detail")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["signal"]["id"] == str(signal.id)
        assert body["signal"]["symbol"] == "ETHUSDT"
        assert body["outcome"] is not None
        assert body["outcome"]["was_correct"] is True
        assert body["outcome"]["price_at_signal"] == 3000.0

    @pytest.mark.asyncio
    async def test_get_signal_detail_without_outcome(
        self,
        client: AsyncClient,
        seed_signals: list[TradingSignalOrm],
    ) -> None:
        """GET /{signal_id}/detail returns null outcome when none recorded."""
        signal = seed_signals[0]
        resp = await client.get(f"/api/v1/signals/{signal.id}/detail")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["signal"]["id"] == str(signal.id)
        assert body["outcome"] is None

    @pytest.mark.asyncio
    async def test_get_signal_detail_not_found(self, client: AsyncClient) -> None:
        """GET /{signal_id}/detail returns 404 for an unknown ID."""
        unknown_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/signals/{unknown_id}/detail")
        assert resp.status_code == 404

    # --- /performance ---

    @pytest.mark.asyncio
    async def test_get_signal_performance_empty(self, client: AsyncClient) -> None:
        """GET /performance returns zeroed stats when no signals exist."""
        resp = await client.get("/api/v1/signals/performance")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_signals"] == 0
        assert data["evaluated_signals"] == 0
        assert data["correct_signals"] == 0
        assert data["win_rate"] is None

    @pytest.mark.asyncio
    async def test_get_signal_performance(
        self,
        client: AsyncClient,
        seed_signal_with_outcome: tuple[TradingSignalOrm, SignalOutcomeOrm],
    ) -> None:
        """GET /performance reflects inserted signals and outcomes."""
        resp = await client.get("/api/v1/signals/performance")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_signals"] >= 1
        assert data["evaluated_signals"] >= 1
        assert data["correct_signals"] >= 1
        # win_rate is a percentage value when outcomes exist
        assert data["win_rate"] is not None
        assert 0.0 <= data["win_rate"] <= 100.0
