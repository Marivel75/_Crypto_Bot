"""ML worker entry point — runs signal generation on a schedule."""

from __future__ import annotations

import asyncio
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.shared.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_signal_generation() -> None:
    """Execute one round of signal generation."""
    from src.ml.signal_generator import generate_signals_for_symbols

    try:
        results = await generate_signals_for_symbols()
        total = sum(results.values())
        logger.info("Signal generation run complete: %d signals emitted", total)
    except Exception:
        logger.exception("Signal generation run failed")


async def _async_main() -> None:
    """Async entry point — run once then schedule periodic execution."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_signal_generation,
        "interval",
        minutes=15,
        id="signal_generation",
        name="Generate trading signals",
    )

    stop_event = asyncio.Event()

    def _shutdown(*_: object) -> None:
        logger.info("ML worker shutting down")
        scheduler.shutdown(wait=False)
        stop_event.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("ML worker starting — signal generation every 15 minutes")

    # Run once at startup
    await run_signal_generation()

    scheduler.start()

    # Block until shutdown signal
    await stop_event.wait()


def main() -> None:
    """Start the ML worker with a periodic scheduler."""
    try:
        asyncio.run(_async_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ML worker stopped")


if __name__ == "__main__":
    main()
