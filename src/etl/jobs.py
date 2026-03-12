"""ETL scheduled jobs — each function is a standalone job for APScheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from src.etl.transformers.cleaner import deduplicate_ohlcv
from src.shared.constants import PRIORITY_SYMBOLS, TRACKED_SYMBOLS
from src.shared.models.crypto import OHLCVRecord

logger = logging.getLogger(__name__)

_CONCURRENCY = asyncio.Semaphore(5)


async def _fetch_symbol(
    collector: object,
    symbol: str,
    timeframe: str,
) -> list[OHLCVRecord]:
    """Fetch OHLCV for one symbol/timeframe with concurrency limit."""
    from src.etl.collectors.binance import BinanceCollector

    async with _CONCURRENCY:
        if not isinstance(collector, BinanceCollector):
            raise TypeError(f"Expected BinanceCollector, got {type(collector).__name__}")
        return await collector.fetch_ohlcv(symbol, timeframe, limit=500)


async def job_collect_ohlcv_priority() -> None:
    """Collect 1-minute OHLCV for priority (top 13) symbols."""
    from src.etl.collectors.binance import BinanceCollector
    from src.etl.loaders.timescaledb import insert_ohlcv_batch
    from src.etl.transformers.cleaner import filter_valid_records

    logger.info("Starting job: collect_ohlcv_priority")
    try:
        async with BinanceCollector() as collector:
            tasks = [_fetch_symbol(collector, symbol, "1m") for symbol in PRIORITY_SYMBOLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_records: list[OHLCVRecord] = []
            for sym, result in zip(PRIORITY_SYMBOLS, results, strict=False):
                if isinstance(result, BaseException):
                    logger.error("Failed to fetch %s: %s", sym, result)
                    continue
                all_records.extend(result)

            if all_records:
                all_records = deduplicate_ohlcv(all_records)
                valid, invalid = filter_valid_records(all_records)
                inserted = await insert_ohlcv_batch(valid)
                logger.info(
                    "job_collect_ohlcv_priority complete: %d fetched, %d valid, %d inserted",
                    len(all_records),
                    len(valid),
                    inserted,
                )
    except Exception:
        logger.exception("job_collect_ohlcv_priority failed")


async def job_collect_ohlcv_all() -> None:
    """Collect 5-minute OHLCV for all tracked symbols."""
    from src.etl.collectors.binance import BinanceCollector
    from src.etl.loaders.timescaledb import insert_ohlcv_batch
    from src.etl.transformers.cleaner import filter_valid_records

    logger.info("Starting job: collect_ohlcv_all")
    try:
        async with BinanceCollector() as collector:
            tasks = [_fetch_symbol(collector, symbol, "5m") for symbol in TRACKED_SYMBOLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_records: list[OHLCVRecord] = []
            for sym, result in zip(TRACKED_SYMBOLS, results, strict=False):
                if isinstance(result, BaseException):
                    logger.error("Failed to fetch %s: %s", sym, result)
                    continue
                all_records.extend(result)

            if all_records:
                all_records = deduplicate_ohlcv(all_records)
                valid, _invalid = filter_valid_records(all_records)
                inserted = await insert_ohlcv_batch(valid)
                logger.info(
                    "job_collect_ohlcv_all complete: %d valid, %d inserted",
                    len(valid),
                    inserted,
                )
    except Exception:
        logger.exception("job_collect_ohlcv_all failed")


async def job_collect_market_data() -> None:
    """Collect market data from CoinGecko for all tracked symbols.

    Persists raw JSON to MinIO and stores a ``MARKET_DATA`` pseudo-OHLCV
    record with total_market_cap (volume_24h) and BTC dominance (price_close).
    """
    from decimal import Decimal

    from src.etl.collectors.coingecko import CoinGeckoCollector
    from src.etl.loaders.minio_loader import upload_raw_json
    from src.etl.loaders.timescaledb import insert_ohlcv_batch
    from src.shared.config import settings

    logger.info("Starting job: collect_market_data")
    try:
        async with CoinGeckoCollector() as collector:
            data = await collector.fetch_market_data(settings.tracked_symbols)
            if data:
                date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
                await upload_raw_json(
                    data,
                    "raw",
                    f"coingecko/markets/{date_str}/market_data.json",
                )

                total_market_cap = Decimal("0")
                btc_market_cap = Decimal("0")
                for coin in data:
                    mc = coin.get("market_cap")
                    if mc is not None:
                        total_market_cap += Decimal(str(mc))
                    symbol_upper = str(coin.get("symbol", "")).upper()
                    if symbol_upper == "BTC" and mc is not None:
                        btc_market_cap = Decimal(str(mc))

                btc_dominance = (
                    (btc_market_cap / total_market_cap * 100)
                    if total_market_cap > 0
                    else Decimal("0")
                )

                now = datetime.now(tz=UTC)
                market_record = OHLCVRecord(
                    symbol="MARKET_DATA",
                    price_open=Decimal("0"),
                    price_high=Decimal("0"),
                    price_low=Decimal("0"),
                    price_close=btc_dominance,
                    volume_24h=total_market_cap,
                    market_cap=total_market_cap,
                    timestamp=now,
                    source="coingecko",
                    timeframe="1D",
                )
                await insert_ohlcv_batch([market_record])

                logger.info(
                    "job_collect_market_data complete: %d coins, market_cap=%s, btc_dom=%.2f%%",
                    len(data),
                    total_market_cap,
                    btc_dominance,
                )
    except Exception:
        logger.exception("job_collect_market_data failed")


async def job_collect_news() -> None:
    """Collect news articles from RSS feeds."""
    from src.etl.collectors.news import NewsCollector
    from src.etl.loaders.timescaledb import insert_news_batch

    logger.info("Starting job: collect_news")
    try:
        async with NewsCollector() as collector:
            articles = await collector.fetch_news()
            if articles:
                inserted = await insert_news_batch(articles)
                logger.info(
                    "job_collect_news complete: %d fetched, %d inserted",
                    len(articles),
                    inserted,
                )
    except Exception:
        logger.exception("job_collect_news failed")


async def job_collect_fear_greed() -> None:
    """Collect Fear & Greed Index from Alternative.me and persist as pseudo-OHLCV."""
    from src.etl.collectors.fear_greed import FearGreedCollector
    from src.etl.loaders.timescaledb import insert_ohlcv_batch

    logger.info("Starting job: collect_fear_greed")
    try:
        async with FearGreedCollector() as collector:
            records = await collector.fetch_as_ohlcv()
            inserted = await insert_ohlcv_batch(records)
        logger.info(
            "job_collect_fear_greed complete: %d records inserted",
            inserted,
        )
    except Exception:
        logger.exception("job_collect_fear_greed failed")


async def job_compute_indicators() -> None:
    """Compute technical indicators for all symbols and applicable timeframes."""
    from src.etl.loaders.timescaledb import (
        fetch_ohlcv_for_indicators,
        insert_indicators_batch,
    )
    from src.etl.transformers.indicators import compute_indicators_for_symbol
    from src.shared.constants import RSI_BB_TIMEFRAMES, TREND_TIMEFRAMES

    logger.info("Starting job: compute_indicators")
    try:
        all_timeframes = set(RSI_BB_TIMEFRAMES) | set(TREND_TIMEFRAMES)

        async def _compute_one(symbol: str, timeframe: str) -> int:
            async with _CONCURRENCY:
                rows = await fetch_ohlcv_for_indicators(symbol, timeframe, limit=500)
                if len(rows) < 20:
                    return 0
                indicators = compute_indicators_for_symbol(rows, symbol, timeframe)
                if indicators:
                    return await insert_indicators_batch(indicators)
                return 0

        tasks = [_compute_one(s, tf) for s in TRACKED_SYMBOLS for tf in all_timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_inserted = 0
        for result in results:
            if isinstance(result, BaseException):
                logger.error("Indicator computation failed: %s", result)
            else:
                total_inserted += result

        logger.info("job_compute_indicators complete: %d records upserted", total_inserted)
    except Exception:
        logger.exception("job_compute_indicators failed")


async def job_export_datasets() -> None:
    """Export OHLCV + indicators as Parquet datasets to MinIO for ML team."""
    from src.etl.loaders.minio_loader import upload_ohlcv_parquet
    from src.etl.loaders.timescaledb import fetch_ohlcv_for_indicators

    logger.info("Starting job: export_datasets")
    try:
        date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")

        async def _export_one(symbol: str) -> int:
            async with _CONCURRENCY:
                rows = await fetch_ohlcv_for_indicators(symbol, "4h", limit=500)
                if rows:
                    await upload_ohlcv_parquet(rows, symbol, date_str)
                    return 1
                return 0

        results = await asyncio.gather(*[_export_one(s) for s in TRACKED_SYMBOLS], return_exceptions=True)
        exported = sum(r for r in results if isinstance(r, int))
        for r in results:
            if isinstance(r, BaseException):
                logger.error("Dataset export failed: %s", r)

        logger.info("job_export_datasets complete: %d symbols exported", exported)
    except Exception:
        logger.exception("job_export_datasets failed")


async def job_reconciliation() -> None:
    """Detect gaps in OHLCV data and attempt backfill."""
    from datetime import timedelta

    from src.etl.collectors.binance import BinanceCollector
    from src.etl.loaders.timescaledb import detect_gaps, insert_ohlcv_batch

    logger.info("Starting job: reconciliation")
    try:
        since = datetime.now(tz=UTC) - timedelta(hours=24)
        timeframe = "1h"
        interval_seconds = 3600

        async with BinanceCollector() as collector:

            async def _reconcile_one(symbol: str) -> None:
                async with _CONCURRENCY:
                    gaps = await detect_gaps(symbol, timeframe, interval_seconds, since)
                    if gaps:
                        logger.info(
                            "Backfilling %d gaps for %s/%s",
                            len(gaps),
                            symbol,
                            timeframe,
                        )
                        records = await collector.fetch_ohlcv(symbol, timeframe, limit=100)
                        if records:
                            await insert_ohlcv_batch(records)

            results = await asyncio.gather(*[_reconcile_one(s) for s in PRIORITY_SYMBOLS], return_exceptions=True)
            for sym, r in zip(PRIORITY_SYMBOLS, results, strict=False):
                if isinstance(r, BaseException):
                    logger.error("Reconciliation failed for %s: %s", sym, r)

        logger.info("job_reconciliation complete")
    except Exception:
        logger.exception("job_reconciliation failed")


async def job_evaluate_signal_outcomes() -> None:
    """Evaluate past signals by comparing predicted direction to actual price moves.

    For each unevaluated signal older than 1h, fetch the price at signal time
    and at +1h, +4h, +1d. Compute simulated P&L and correctness, then persist
    the outcome record.
    """
    from datetime import timedelta

    from src.etl.loaders.timescaledb import (
        fetch_price_at_time,
        fetch_unevaluated_signals,
        insert_signal_outcome,
    )

    logger.info("Starting job: evaluate_signal_outcomes")
    try:
        signals = await fetch_unevaluated_signals()
        if not signals:
            logger.info("job_evaluate_signal_outcomes: no signals to evaluate")
            return

        evaluated = 0
        for sig in signals:
            signal_id = str(sig["id"])
            symbol = str(sig["symbol"])
            signal_type = str(sig["signal_type"])
            created_at: datetime = sig["created_at"]  # type: ignore[assignment]

            price_at = await fetch_price_at_time(symbol, created_at)
            if price_at is None:
                continue

            price_1h = await fetch_price_at_time(symbol, created_at + timedelta(hours=1))
            price_4h = await fetch_price_at_time(symbol, created_at + timedelta(hours=4))
            price_1d = await fetch_price_at_time(symbol, created_at + timedelta(days=1))

            # Determine correctness using the longest available horizon
            ref_price = price_1d or price_4h or price_1h
            was_correct: bool | None = None
            pnl_simulated: float | None = None

            if ref_price is not None and price_at > 0:
                pct_change = (ref_price - price_at) / price_at * 100
                pnl_simulated = round(pct_change, 4)
                if signal_type == "BUY":
                    was_correct = ref_price > price_at
                elif signal_type == "SELL":
                    was_correct = ref_price < price_at
                else:
                    was_correct = abs(pct_change) < 1.0

            await insert_signal_outcome(
                signal_id=signal_id,
                price_at_signal=price_at,
                price_after_1h=price_1h,
                price_after_4h=price_4h,
                price_after_1d=price_1d,
                pnl_simulated=pnl_simulated,
                was_correct=was_correct,
            )
            evaluated += 1

        logger.info("job_evaluate_signal_outcomes complete: %d signals evaluated", evaluated)
    except Exception:
        logger.exception("job_evaluate_signal_outcomes failed")
