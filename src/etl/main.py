"""ETL service entry point — sets up logging, MinIO, and starts the APScheduler.

Job schedule:
    collect_ohlcv_priority  — every 1 min  (top 13 symbols)
    collect_ohlcv_all       — every 5 min  (all symbols)
    collect_market_data     — every 5 min  (CoinGecko)
    collect_news            — every 15 min (RSS feeds)
    enrich_news_nlp         — every 20 min (sentiment + keywords on new articles)
    collect_fear_greed      — every 60 min (Alternative.me)
    compute_indicators      — every 5 min  (RSI, Bollinger, trend)
    reconciliation          — every 60 min (gap detection + backfill)
    evaluate_signal_outcomes — every 60 min (compute signal P&L + correctness)
    export_datasets         — daily 03:00  (MinIO Parquet export)
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from aiohttp import web  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]

from src.etl.jobs import (
    job_collect_fear_greed,
    job_collect_market_data,
    job_collect_news,
    job_collect_ohlcv_all,
    job_collect_ohlcv_priority,
    job_compute_indicators,
    job_enrich_news_nlp,
    job_evaluate_signal_outcomes,
    job_export_datasets,
    job_reconciliation,
)
from src.shared.utils import setup_logging

logger = logging.getLogger(__name__)

_HEALTH_PORT = 8080


async def _health_handler(_request: web.Request) -> web.Response:
    """Health check for Docker / load balancer."""
    return web.Response(text="OK", status=200)


def build_scheduler() -> AsyncIOScheduler:
    """Construct and return the APScheduler with all ETL jobs registered."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        job_collect_ohlcv_priority,
        "interval",
        minutes=1,
        id="collect_ohlcv_priority",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_collect_ohlcv_all,
        "interval",
        minutes=5,
        id="collect_ohlcv_all",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_collect_market_data,
        "interval",
        minutes=5,
        id="collect_market_data",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_collect_news,
        "interval",
        minutes=15,
        id="collect_news",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_enrich_news_nlp,
        "interval",
        minutes=20,
        id="enrich_news_nlp",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_collect_fear_greed,
        "interval",
        hours=1,
        id="collect_fear_greed",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_compute_indicators,
        "interval",
        minutes=5,
        id="compute_indicators",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_export_datasets,
        "cron",
        hour=3,
        minute=0,
        id="export_datasets",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_reconciliation,
        "interval",
        hours=1,
        id="reconciliation",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        job_evaluate_signal_outcomes,
        "interval",
        hours=1,
        id="evaluate_signal_outcomes",
        max_instances=1,
        coalesce=True,
    )

    return scheduler


async def _ensure_minio() -> None:
    """Create required MinIO buckets, logging a warning if unreachable."""
    from src.etl.loaders.minio_loader import ensure_buckets_exist

    try:
        await ensure_buckets_exist()
        logger.info("MinIO buckets verified")
    except Exception:
        logger.warning(
            "Could not verify MinIO buckets (will retry on first export)",
            exc_info=True,
        )


async def main() -> None:
    """Start the ETL worker and block until a shutdown signal is received."""
    setup_logging("src.etl")
    logger.info("ETL worker starting")

    await _ensure_minio()

    scheduler = build_scheduler()
    scheduler.start()
    logger.info(
        "Scheduler started with %d jobs: %s",
        len(scheduler.get_jobs()),
        [j.id for j in scheduler.get_jobs()],
    )

    # Health check HTTP server
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _HEALTH_PORT)  # noqa: S104
    await site.start()
    logger.info("Health check on port %d", _HEALTH_PORT)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Received signal %s — shutting down", sig.name)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    try:
        await stop_event.wait()
    finally:
        logger.info("ETL worker shutting down")
        scheduler.shutdown(wait=False)
        await runner.cleanup()
        logger.info("ETL worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ETL worker interrupted")
        sys.exit(0)
