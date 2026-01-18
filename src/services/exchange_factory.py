"""
Factory d'exchanges pour gérer plusieurs plateformes.

Ce module fournit une interface unifiée pour créer et utiliser différents
clients d'exchange (Binance, Kraken, etc.).
"""

from typing import Any, Union

from src.config.logger_settings import logger
from src.services.exchanges_api.binance_client import BinanceClient
from src.services.exchanges_api.coinbase_client import CoinbaseClient
from src.services.exchanges_api.kraken_client import KrakenClient

ExchangeClient = Union[BinanceClient, KrakenClient, CoinbaseClient]


class ExchangeFactory:
    """
    Factory pour créer et gérer des clients d'exchange.
    Classe unifiée pour accéder à différents exchanges via leurs clients respectifs.
    """

    @staticmethod
    def create_exchange(exchange_name: str, **kwargs: Any) -> ExchangeClient:
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
        return ["binance", "kraken", "coinbase"]


def get_exchange_client(
    exchange_name: str,
) -> ExchangeClient:
    """
    Fonction utilitaire pour obtenir un client d'exchange sans instancier la classe.

    Args:
        exchange_name: Nom de l'exchange

    Returns:
        Instance du client d'exchange
    """
    return ExchangeFactory.create_exchange(exchange_name)
