"""
Factory d'exchanges pour gérer plusieurs plateformes.

Ce module fournit une interface unifiée pour créer et utiliser
différents clients d'exchange (Binance, Kraken, etc.).
"""

from src.services.binance_client import BinanceClient
from src.services.kraken_client import KrakenClient
from logger_settings import logger
from typing import Union


class ExchangeFactory:
    """
    Fabrique pour créer et gérer des clients d'exchange.
    Classe unifiée pour accéder à différents exchanges via leurs clients respectifs.
    """
    
    @staticmethod
    def create_exchange(exchange_name: str, **kwargs) -> Union[BinanceClient, KrakenClient]:
        """
        Crée une instance de client pour l'exchange spécifié.
        
        Args:
            exchange_name: Nom de l'exchange ('binance' ou 'kraken')
            **kwargs: Arguments supplémentaires pour le client
            
        Returns:
            Instance du client d'exchange
            
        Raises:
            ValueError: Si l'exchange n'est pas supporté
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name == 'binance':
            logger.info("Création du client Binance")
            return BinanceClient()
        
        elif exchange_name == 'kraken':
            logger.info("Création du client Kraken")
            # Pour les données publiques, pas d'authentification
            return KrakenClient(use_auth=False)
        
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
        return ['binance', 'kraken']


def get_exchange_client(exchange_name: str) -> Union[BinanceClient, KrakenClient]:
    """
    Fonction utilitaire pour obtenir un client d'exchange.
    
    Args:
        exchange_name: Nom de l'exchange
        
    Returns:
        Instance du client d'exchange
    """
    return ExchangeFactory.create_exchange(exchange_name)