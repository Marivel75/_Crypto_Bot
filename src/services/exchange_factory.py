"""
Factory d'exchanges pour gérer plusieurs plateformes.

Ce module fournit une interface unifiée pour créer et utiliser différents clients d'exchange (Binance, Kraken, etc.).
"""

from src.services.exchanges_api.binance_client import BinanceClient
from src.services.exchanges_api.kraken_client import KrakenClient
from src.services.exchanges_api.coinbase_client import CoinbaseClient
from src.services.exchanges_api.coingecko_client import CoinGeckoClient
from logger_settings import logger
from typing import Union


class ExchangeFactory:
    """
    Factory pour créer et gérer des clients d'exchange.
    Classe pour accéder à différents exchanges via leurs clients respectifs.
    """

    @staticmethod
    def create_exchange(
        exchange_name: str, **kwargs
    ) -> Union[BinanceClient, KrakenClient, CoinbaseClient, CoinGeckoClient]:
        """
        Crée une instance de client pour l'exchange spécifié.
        """
        exchange_name = exchange_name.lower()

        if exchange_name == "binance":
            logger.info("Création du client Binance")
            return BinanceClient()

        elif exchange_name == "kraken":
            logger.info("Création du client Kraken")
            # Pour les données publiques, pas d'authentification
            return KrakenClient(use_auth=False)

        elif exchange_name == "coinbase":
            logger.info("Création du client Coinbase")
            # Pour les données publiques, pas d'authentification
            return CoinbaseClient(use_auth=False)

        elif exchange_name == "coingecko":
            logger.info("Création du client CoinGecko")
            rate_limit_delay = kwargs.get("rate_limit_delay", 0.3)
            return CoinGeckoClient(rate_limit_delay=rate_limit_delay)

        else:
            error_msg = f"Exchange non supporté: {exchange_name}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def get_supported_exchanges() -> list:
        """
        Retourne la liste des exchanges supportés.

        Returns:
            list: Liste des noms d'exchanges supportés
        """
        return ["binance", "kraken", "coinbase", "coingecko"]


def get_exchange_client(
    exchange_name: str,
    **kwargs,
) -> Union[BinanceClient, KrakenClient, CoinbaseClient, CoinGeckoClient]:
    """
    Fonction utilitaire pour obtenir un client d'exchange sans instancier la classe.

    Args:
        exchange_name: Nom de l'exchange
        **kwargs: Arguments additionnels (ex: rate_limit_delay pour CoinGecko)

    Returns:
        Instance du client d'exchange
    """
    return ExchangeFactory.create_exchange(exchange_name, **kwargs)
