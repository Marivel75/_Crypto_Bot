"""Unit tests for new ETL job features and CCXTCollector.

Covers:
- job_collect_fear_greed: fetch_as_ohlcv + insert_ohlcv_batch wiring
- job_collect_market_data: MinIO upload, MARKET_DATA record persistence, empty data
- job_evaluate_signal_outcomes: skip on no signals, BUY/SELL correctness, None price guard
- CCXTCollector: symbol conversion, candle parsing, unsupported timeframe
- get_market_overview: FEAR_GREED and MARKET_DATA pseudo-OHLCV queries
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

UTC = timezone.utc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import ExternalAPIError
from src.shared.models.crypto import OHLCVRecord

# Import test-compatible ORM from conftest (SQLite-safe)
from tests.conftest import CryptoPriceOrm

# Fixed timestamps — never datetime.now() in tests
_TS = datetime(2025, 3, 7, 10, 0, 0, tzinfo=UTC)
_TS2 = datetime(2025, 3, 7, 11, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv_record(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    price_close: Decimal = Decimal("50000"),
    ts: datetime = _TS,
) -> OHLCVRecord:
    """Return a minimal valid OHLCVRecord."""
    return OHLCVRecord(
        symbol=symbol,
        price_open=price_close,
        price_high=price_close,
        price_low=price_close,
        price_close=price_close,
        volume_24h=Decimal("1000000"),
        market_cap=None,
        timestamp=ts,
        source="test",
        timeframe=timeframe,
    )


def _make_price_row(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    price_close: float = 50000.0,
    volume_24h: float = 1_000_000.0,
    ts: datetime = _TS,
) -> CryptoPriceOrm:
    """Return an unsaved CryptoPriceOrm row."""
    return CryptoPriceOrm(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        price_open=price_close,
        price_high=price_close,
        price_low=price_close,
        price_close=price_close,
        volume_24h=volume_24h,
        market_cap=None,
        source="test",
    )


# ---------------------------------------------------------------------------
# job_collect_fear_greed
# ---------------------------------------------------------------------------


class TestJobCollectFearGreed:
    """Tests for job_collect_fear_greed in src/etl/jobs.py."""

    @pytest.mark.asyncio
    async def test_calls_fetch_as_ohlcv_and_insert_ohlcv_batch(self) -> None:
        """Job must call fetch_as_ohlcv then pass records to insert_ohlcv_batch."""
        records = [_make_ohlcv_record(symbol="FEAR_GREED")]
        mock_collector = AsyncMock()
        mock_collector.fetch_as_ohlcv = AsyncMock(return_value=records)
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.etl.collectors.fear_greed.FearGreedCollector", return_value=mock_collector),
            patch("src.etl.loaders.timescaledb.insert_ohlcv_batch", new_callable=AsyncMock, return_value=1) as mock_insert,
        ):
            from src.etl.jobs import job_collect_fear_greed

            await job_collect_fear_greed()

        mock_collector.fetch_as_ohlcv.assert_awaited_once()
        mock_insert.assert_awaited_once_with(records)

    @pytest.mark.asyncio
    async def test_logs_exception_on_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Job must log an exception when the collector raises."""
        mock_collector = AsyncMock()
        mock_collector.fetch_as_ohlcv = AsyncMock(side_effect=RuntimeError("connection refused"))
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.etl.collectors.fear_greed.FearGreedCollector", return_value=mock_collector),
            patch("src.etl.loaders.timescaledb.insert_ohlcv_batch", new_callable=AsyncMock),
            caplog.at_level(logging.ERROR, logger="src.etl.jobs"),
        ):
            from src.etl.jobs import job_collect_fear_greed

            await job_collect_fear_greed()

        assert any("job_collect_fear_greed" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# job_collect_market_data
# ---------------------------------------------------------------------------


class TestJobCollectMarketData:
    """Tests for job_collect_market_data in src/etl/jobs.py."""

    def _market_data_payload(self) -> list[dict]:
        """Return a minimal CoinGecko market-data API response."""
        return [
            {"symbol": "btc", "market_cap": 1_000_000_000},
            {"symbol": "eth", "market_cap": 500_000_000},
        ]

    @pytest.mark.asyncio
    async def test_uploads_raw_json_to_minio(self) -> None:
        """Job must call upload_raw_json with the fetched market data."""
        data = self._market_data_payload()
        mock_collector = AsyncMock()
        mock_collector.fetch_market_data = AsyncMock(return_value=data)
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.etl.collectors.coingecko.CoinGeckoCollector", return_value=mock_collector),
            patch("src.etl.loaders.minio_loader.upload_raw_json", new_callable=AsyncMock) as mock_upload,
            patch("src.etl.loaders.timescaledb.insert_ohlcv_batch", new_callable=AsyncMock, return_value=1),
        ):
            from src.etl.jobs import job_collect_market_data

            await job_collect_market_data()

        mock_upload.assert_awaited_once()
        call_args = mock_upload.call_args
        # First positional arg is the data payload
        assert call_args.args[0] == data

    @pytest.mark.asyncio
    async def test_persists_market_data_ohlcv_record(self) -> None:
        """Job must insert a MARKET_DATA pseudo-OHLCV record with correct values."""
        data = self._market_data_payload()
        mock_collector = AsyncMock()
        mock_collector.fetch_market_data = AsyncMock(return_value=data)
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.etl.collectors.coingecko.CoinGeckoCollector", return_value=mock_collector),
            patch("src.etl.loaders.minio_loader.upload_raw_json", new_callable=AsyncMock),
            patch("src.etl.loaders.timescaledb.insert_ohlcv_batch", new_callable=AsyncMock, return_value=1) as mock_insert,
        ):
            from src.etl.jobs import job_collect_market_data

            await job_collect_market_data()

        mock_insert.assert_awaited_once()
        inserted_records: list[OHLCVRecord] = mock_insert.call_args.args[0]
        assert len(inserted_records) == 1
        record = inserted_records[0]

        expected_total = Decimal("1500000000")
        expected_btc_dom = Decimal("1000000000") / expected_total * 100

        assert record.symbol == "MARKET_DATA"
        assert record.volume_24h == expected_total
        assert record.market_cap == expected_total
        assert record.timeframe == "1D"
        assert record.source == "coingecko"
        # price_close encodes BTC dominance
        assert abs(record.price_close - expected_btc_dom) < Decimal("0.0001")

    @pytest.mark.asyncio
    async def test_handles_empty_data_gracefully(self) -> None:
        """Job must not call insert_ohlcv_batch when collector returns empty list."""
        mock_collector = AsyncMock()
        mock_collector.fetch_market_data = AsyncMock(return_value=[])
        mock_collector.__aenter__ = AsyncMock(return_value=mock_collector)
        mock_collector.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.etl.collectors.coingecko.CoinGeckoCollector", return_value=mock_collector),
            patch("src.etl.loaders.minio_loader.upload_raw_json", new_callable=AsyncMock) as mock_upload,
            patch("src.etl.loaders.timescaledb.insert_ohlcv_batch", new_callable=AsyncMock) as mock_insert,
        ):
            from src.etl.jobs import job_collect_market_data

            await job_collect_market_data()

        mock_upload.assert_not_awaited()
        mock_insert.assert_not_awaited()


# ---------------------------------------------------------------------------
# job_evaluate_signal_outcomes
# ---------------------------------------------------------------------------


class TestJobEvaluateSignalOutcomes:
    """Tests for job_evaluate_signal_outcomes in src/etl/jobs.py."""

    @pytest.mark.asyncio
    async def test_skips_when_no_unevaluated_signals(self, caplog: pytest.LogCaptureFixture) -> None:
        """Job must return early and log info when no signals are pending."""
        with (
            patch("src.etl.loaders.timescaledb.fetch_unevaluated_signals", new_callable=AsyncMock, return_value=[]),
            patch("src.etl.loaders.timescaledb.fetch_price_at_time", new_callable=AsyncMock) as mock_price,
            patch("src.etl.loaders.timescaledb.insert_signal_outcome", new_callable=AsyncMock) as mock_outcome,
            caplog.at_level(logging.INFO, logger="src.etl.jobs"),
        ):
            from src.etl.jobs import job_evaluate_signal_outcomes

            await job_evaluate_signal_outcomes()

        mock_price.assert_not_awaited()
        mock_outcome.assert_not_awaited()
        assert any("no signals" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_buy_signal_correct_when_price_rose(self) -> None:
        """BUY signal is was_correct=True when ref_price > price_at_signal."""
        signal = {
            "id": "sig-001",
            "symbol": "BTCUSDT",
            "signal_type": "BUY",
            "created_at": _TS,
        }
        price_at = 50000.0
        price_1h = None
        price_4h = None
        price_1d = 51000.0  # price went up

        def _fake_fetch_price(symbol: str, ts: datetime) -> float | None:
            if ts == _TS:
                return price_at
            if ts.hour == _TS.hour + 1:
                return price_1h
            if ts.hour == _TS.hour + 4:
                return price_4h
            return price_1d

        with (
            patch("src.etl.loaders.timescaledb.fetch_unevaluated_signals", new_callable=AsyncMock, return_value=[signal]),
            patch("src.etl.loaders.timescaledb.fetch_price_at_time", side_effect=_fake_fetch_price),
            patch("src.etl.loaders.timescaledb.insert_signal_outcome", new_callable=AsyncMock) as mock_outcome,
        ):
            from src.etl.jobs import job_evaluate_signal_outcomes

            await job_evaluate_signal_outcomes()

        mock_outcome.assert_awaited_once()
        kwargs = mock_outcome.call_args.kwargs
        assert kwargs["was_correct"] is True
        assert kwargs["signal_id"] == "sig-001"
        # pnl should be positive
        assert kwargs["pnl_simulated"] is not None
        assert kwargs["pnl_simulated"] > 0

    @pytest.mark.asyncio
    async def test_sell_signal_correct_when_price_fell(self) -> None:
        """SELL signal is was_correct=True when ref_price < price_at_signal."""
        signal = {
            "id": "sig-002",
            "symbol": "ETHUSDT",
            "signal_type": "SELL",
            "created_at": _TS,
        }
        price_at = 3000.0
        price_1d = 2800.0  # price went down

        def _fake_fetch_price(symbol: str, ts: datetime) -> float | None:
            if ts == _TS:
                return price_at
            # +1h and +4h return None; +1d returns lower price
            return price_1d

        with (
            patch("src.etl.loaders.timescaledb.fetch_unevaluated_signals", new_callable=AsyncMock, return_value=[signal]),
            patch("src.etl.loaders.timescaledb.fetch_price_at_time", side_effect=_fake_fetch_price),
            patch("src.etl.loaders.timescaledb.insert_signal_outcome", new_callable=AsyncMock) as mock_outcome,
        ):
            from src.etl.jobs import job_evaluate_signal_outcomes

            await job_evaluate_signal_outcomes()

        kwargs = mock_outcome.call_args.kwargs
        assert kwargs["was_correct"] is True
        assert kwargs["pnl_simulated"] is not None
        assert kwargs["pnl_simulated"] < 0  # pct_change negative for SELL win

    @pytest.mark.asyncio
    async def test_skips_signal_when_price_at_signal_is_none(self) -> None:
        """Job must skip a signal and not call insert_signal_outcome when price_at is None."""
        signal = {
            "id": "sig-003",
            "symbol": "BTCUSDT",
            "signal_type": "BUY",
            "created_at": _TS,
        }

        with (
            patch("src.etl.loaders.timescaledb.fetch_unevaluated_signals", new_callable=AsyncMock, return_value=[signal]),
            patch("src.etl.loaders.timescaledb.fetch_price_at_time", new_callable=AsyncMock, return_value=None),
            patch("src.etl.loaders.timescaledb.insert_signal_outcome", new_callable=AsyncMock) as mock_outcome,
        ):
            from src.etl.jobs import job_evaluate_signal_outcomes

            await job_evaluate_signal_outcomes()

        mock_outcome.assert_not_awaited()


# ---------------------------------------------------------------------------
# CCXTCollector
# ---------------------------------------------------------------------------


class TestCCXTCollectorToSymbol:
    """Tests for CCXTCollector._to_ccxt_symbol."""

    def test_converts_btcusdt_to_ccxt_format(self) -> None:
        """BTCUSDT must convert to BTC/USDT."""
        from src.etl.collectors.ccxt_collector import CCXTCollector

        result = CCXTCollector._to_ccxt_symbol("BTCUSDT")
        assert result == "BTC/USDT"

    def test_converts_ethusdt_to_ccxt_format(self) -> None:
        """ETHUSDT must convert to ETH/USDT."""
        from src.etl.collectors.ccxt_collector import CCXTCollector

        result = CCXTCollector._to_ccxt_symbol("ETHUSDT")
        assert result == "ETH/USDT"

    def test_converts_bnbbtc_to_ccxt_format(self) -> None:
        """BNBBTC must convert to BNB/BTC (quote=BTC)."""
        from src.etl.collectors.ccxt_collector import CCXTCollector

        result = CCXTCollector._to_ccxt_symbol("BNBBTC")
        assert result == "BNB/BTC"

    def test_raises_for_unknown_symbol(self) -> None:
        """Symbols with no recognised quote currency must raise ExternalAPIError."""
        from src.etl.collectors.ccxt_collector import CCXTCollector

        with pytest.raises(ExternalAPIError, match="Cannot convert symbol"):
            CCXTCollector._to_ccxt_symbol("UNKNOWNXYZ")


class TestCCXTCollectorParseCandle:
    """Tests for CCXTCollector._parse_candle."""

    def test_parse_candle_creates_correct_ohlcv_record(self) -> None:
        """_parse_candle must map [ts, O, H, L, C, V] to an OHLCVRecord correctly."""
        from src.etl.collectors.ccxt_collector import CCXTCollector

        # CCXT candle format: [timestamp_ms, open, high, low, close, volume]
        ts_ms = int(_TS.timestamp() * 1000)
        candle: list[float] = [float(ts_ms), 49000.0, 51000.0, 48500.0, 50000.0, 1234.56]

        result = CCXTCollector._parse_candle(candle, "BTCUSDT", "1h")

        assert isinstance(result, OHLCVRecord)
        assert result.symbol == "BTCUSDT"
        assert result.timeframe == "1h"
        assert result.price_open == Decimal("49000.0")
        assert result.price_high == Decimal("51000.0")
        assert result.price_low == Decimal("48500.0")
        assert result.price_close == Decimal("50000.0")
        assert result.volume_24h == Decimal("1234.56")
        assert result.market_cap is None
        # Timestamp is derived from ms epoch
        expected_ts = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
        assert result.timestamp == expected_ts


class TestCCXTCollectorFetchOhlcv:
    """Tests for CCXTCollector.fetch_ohlcv."""

    @pytest.mark.asyncio
    async def test_raises_value_error_for_unsupported_timeframe(self) -> None:
        """fetch_ohlcv must raise ValueError immediately for unknown timeframe strings."""
        mock_exchange = MagicMock()
        mock_exchange.id = "binance"

        with patch("src.etl.collectors.ccxt_collector.ccxt_async") as mock_ccxt:
            mock_ccxt.binance.return_value = mock_exchange
            from src.etl.collectors.ccxt_collector import CCXTCollector

            collector = CCXTCollector(exchange_id="binance")

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            await collector.fetch_ohlcv("BTCUSDT", "3d")


# ---------------------------------------------------------------------------
# get_market_overview — FEAR_GREED and MARKET_DATA wiring
# ---------------------------------------------------------------------------


class TestGetMarketOverviewPseudoOHLCV:
    """Tests for the FEAR_GREED and MARKET_DATA queries in get_market_overview."""

    @pytest.mark.asyncio
    async def test_returns_fear_greed_none_when_no_record_exists(
        self, db_session: AsyncSession
    ) -> None:
        """fear_greed must be None when no FEAR_GREED row is in the DB."""
        from src.api.services.crypto_service import get_market_overview

        result = await get_market_overview(db_session)

        assert result["fear_greed"] is None

    @pytest.mark.asyncio
    async def test_returns_fear_greed_value_when_record_exists(
        self, db_session: AsyncSession
    ) -> None:
        """fear_greed must be the integer value from the most recent FEAR_GREED row."""
        row = _make_price_row(symbol="FEAR_GREED", timeframe="1D", price_close=72.0, ts=_TS)
        db_session.add(row)
        await db_session.commit()

        from src.api.services.crypto_service import get_market_overview

        result = await get_market_overview(db_session)

        assert result["fear_greed"] == 72

    @pytest.mark.asyncio
    async def test_returns_most_recent_fear_greed_when_multiple_records(
        self, db_session: AsyncSession
    ) -> None:
        """get_market_overview must return the latest FEAR_GREED value, not an older one."""
        old_row = _make_price_row(symbol="FEAR_GREED", timeframe="1D", price_close=30.0, ts=_TS)
        new_row = _make_price_row(symbol="FEAR_GREED", timeframe="1D", price_close=65.0, ts=_TS2)
        db_session.add(old_row)
        db_session.add(new_row)
        await db_session.commit()

        from src.api.services.crypto_service import get_market_overview

        result = await get_market_overview(db_session)

        assert result["fear_greed"] == 65

    @pytest.mark.asyncio
    async def test_returns_market_cap_and_btc_dominance_when_record_exists(
        self, db_session: AsyncSession
    ) -> None:
        """total_market_cap and btc_dominance must come from the MARKET_DATA row."""
        # volume_24h encodes total_market_cap; price_close encodes btc_dominance
        row = _make_price_row(
            symbol="MARKET_DATA",
            timeframe="1D",
            price_close=66.67,  # btc dominance %
            volume_24h=1_500_000_000_000.0,  # total market cap
            ts=_TS,
        )
        db_session.add(row)
        await db_session.commit()

        from src.api.services.crypto_service import get_market_overview

        result = await get_market_overview(db_session)

        assert result["total_market_cap"] == pytest.approx(1_500_000_000_000.0)
        assert result["btc_dominance"] == pytest.approx(66.67, abs=0.01)

    @pytest.mark.asyncio
    async def test_returns_none_market_cap_when_no_market_data_record(
        self, db_session: AsyncSession
    ) -> None:
        """total_market_cap and btc_dominance must be None when no MARKET_DATA row exists."""
        from src.api.services.crypto_service import get_market_overview

        result = await get_market_overview(db_session)

        assert result["total_market_cap"] is None
        assert result["btc_dominance"] is None
