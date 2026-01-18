import click

from src.config.logger_settings import logger
from src.scheduler import run_once_now, run_scheduler


DEFAULT_PAIRS = ("BTC/USDT", "ETH/USDT")
DEFAULT_TIMEFRAMES = ("1h", "4h")


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
    type=click.Choice(["binance", "kraken", "coinbase"], case_sensitive=False),
    default="binance",
    show_default=True,
    help="Exchange a utiliser.",
)
def run_command(pairs, timeframes, exchange):
    """Execute une collecte immediate."""
    logger.info("Lancement immediat via CLI.")
    run_once_now(list(pairs), list(timeframes), exchange)


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
    default="09:00",
    show_default=True,
    help="Heure quotidienne pour la collecte (format HH:MM).",
)
@click.option(
    "--exchange",
    type=click.Choice(["binance", "kraken", "coinbase"], case_sensitive=False),
    default="binance",
    show_default=True,
    help="Exchange a utiliser.",
)
def schedule_command(pairs, timeframes, schedule_time, exchange):
    """Demarre la planification quotidienne."""
    logger.info("Demarrage du scheduler via CLI.")
    run_scheduler(list(pairs), list(timeframes), schedule_time, exchange)


if __name__ == "__main__":
    cli()
