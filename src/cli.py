import time

import click

from config.settings import config
from src.config.logger_settings import logger
from src.schedulers.scheduler_ohlcv import OHLCVScheduler


def _as_tuple(value, fallback):
    if not value:
        return fallback
    if isinstance(value, (list, tuple, set)):
        return tuple(value)
    return (value,)


def _normalize_exchanges(value):
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).lower() for item in value if item]
    return [str(value).lower()]


DEFAULT_PAIRS = _as_tuple(config.get("pairs"), ("BTC/USDT", "ETH/USDT"))
DEFAULT_TIMEFRAMES = _as_tuple(config.get("timeframes"), ("1h", "4h"))
EXCHANGE_CHOICES = _normalize_exchanges(config.get("exchanges")) or [
    "binance",
    "kraken",
    "coinbase",
]
DEFAULT_EXCHANGE = (config.get("default_exchange") or EXCHANGE_CHOICES[0]).lower()
DEFAULT_SCHEDULE_TIME = config.get("scheduler.schedule_time", "09:00")


@click.group()
def cli():
    """CLI pour orchestrer le scheduler de collecte de donnees marche."""


@cli.command("run")
@click.option(
    "--pair",
    "pairs",
    multiple=True,
    default=DEFAULT_PAIRS,
    show_default=True,
    help="Pair de trading (option repetable).",
)
@click.option(
    "--timeframe",
    "timeframes",
    multiple=True,
    default=DEFAULT_TIMEFRAMES,
    show_default=True,
    help="Timeframe (option repetable).",
)
@click.option(
    "--exchange",
    type=click.Choice(EXCHANGE_CHOICES, case_sensitive=False),
    default=DEFAULT_EXCHANGE,
    show_default=True,
    help="Exchange a utiliser.",
)
def run_command(pairs, timeframes, exchange):
    """Execute une collecte immediate."""
    logger.info("Lancement immediat via CLI.")
    scheduler = OHLCVScheduler(
        pairs=list(pairs),
        timeframes=list(timeframes),
        exchanges=[exchange],
    )
    scheduler.run_once()


@cli.command("schedule")
@click.option(
    "--pair",
    "pairs",
    multiple=True,
    default=DEFAULT_PAIRS,
    show_default=True,
    help="Pair de trading (option repetable).",
)
@click.option(
    "--timeframe",
    "timeframes",
    multiple=True,
    default=DEFAULT_TIMEFRAMES,
    show_default=True,
    help="Timeframe (option repetable).",
)
@click.option(
    "--schedule-time",
    default=DEFAULT_SCHEDULE_TIME,
    show_default=True,
    help="Heure quotidienne pour la collecte (format HH:MM).",
)
@click.option(
    "--exchange",
    type=click.Choice(EXCHANGE_CHOICES, case_sensitive=False),
    default=DEFAULT_EXCHANGE,
    show_default=True,
    help="Exchange a utiliser.",
)
def schedule_command(pairs, timeframes, schedule_time, exchange):
    """Demarre la planification quotidienne."""
    logger.info("Demarrage du scheduler via CLI.")
    scheduler = OHLCVScheduler(
        pairs=list(pairs),
        timeframes=list(timeframes),
        exchanges=[exchange],
        schedule_time=schedule_time,
    )
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Arret du scheduler demande par l'utilisateur.")
        scheduler.stop()


if __name__ == "__main__":
    cli()
