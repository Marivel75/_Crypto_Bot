"""
Client pour l'exchange Coinbase.

Ce module fournit une interface pour interagir avec l'API Coinbase Advanced Trade.
"""

from typing import Any, Dict, List, cast

import ccxt

from src.config.logger_settings import logger


class CoinbaseClient:
    """
    Client pour interagir avec l'API Coinbase Advanced Trade.
    Pour les données de marché publiques, aucune authentification n'est nécessaire.
    Note: Coinbase Advanced Trade nécessite une passphrase en plus des clés API.

    Attributes:
        exchange: Instance ccxt de l'exchange Coinbase Advanced Trade
    """

    def __init__(
        self,
        use_auth: bool = False,
        api_key: str | None = None,
        api_secret: str | None = None,
        api_passphrase: str | None = None,
    ) -> None:
        """
        Initialise le client Coinbase.

        Args:
            use_auth: Si True, utilise l'authentification (pour le trading)
            api_key: Clé API Coinbase (requise si use_auth=True)
            api_secret: Secret API Coinbase (requis si use_auth=True)
            api_passphrase: Passphrase API Coinbase (requise si use_auth=True)

        Raises:
            ValueError: Si use_auth=True mais les clés ne sont pas fournies
        """
        if use_auth:
            if not api_key or not api_secret or not api_passphrase:
                error_msg = (
                    "Les clés API Coinbase (y compris la passphrase) sont requises "
                    "pour les opérations authentifiées"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Initialisation avec authentification pour le trading
            self.exchange = ccxt.coinbase(
                {
                    "apiKey": api_key,
                    "secret": api_secret,
                    "password": api_passphrase,  # Coinbase utilise 'password' pour la passphrase
                    "enableRateLimit": True,
                }
            )
        else:
            # Initialisation sans authentification pour les données publiques
            self.exchange = ccxt.coinbase(
                {
                    "enableRateLimit": True,
                }
            )

        # Synchronisation du temps
        self._sync_time()

        # Vérification de l'initialisation
        self._check_exchange_initialization()

    def _sync_time(self) -> None:
        """
        Synchronisation horloge locale avec Coinbase.
        """
        try:
            server_time = self.exchange.fetch_time()
            self.exchange.options["timeDifference"] = server_time - self.exchange.milliseconds()
            logger.info("Synchronisation de l'heure Coinbase réussie")
        except Exception as e:
            logger.warning(f"Échec de la synchronisation de l'heure Coinbase: {e}")

    def _check_exchange_initialization(self) -> None:
        """
        Vérifie que l'exchange Coinbase est correctement initialisé et accessible.

        Raises:
            RuntimeError: Si l'initialisation échoue
        """
        try:
            # Coinbase ne supporte pas fetch_status(), utiliser fetch_ticker à la place
            test_ticker = self.exchange.fetch_ticker("BTC/USD")
            if test_ticker and "last" in test_ticker:
                logger.info("Initialisation de l'exchange Coinbase réussie")
            else:
                raise RuntimeError("Réponse inattendue de l'API Coinbase")
        except Exception as e:
            logger.error(f"Échec de la vérification de l'initialisation de Coinbase: {e}")
            raise RuntimeError(f"Échec de l'initialisation de l'exchange Coinbase: {e}") from e

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère le ticker pour une paire de trading.

        Args:
            symbol: Paire de trading (ex: 'BTC/USD')

        Returns:
            dict: Informations du ticker

        Raises:
            Exception: En cas d'erreur lors de la récupération
        """
        try:
            return cast(Dict[str, Any], self.exchange.fetch_ticker(symbol))
        except Exception as e:
            logger.error(f"Échec de la récupération du ticker Coinbase pour {symbol}: {e}")
            raise

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[List[Any]]:
        """
        Récupère les données OHLCV pour une paire sur Coinbase Advanced Trade.
        Coinbase Advanced Trade utilise les timeframes standards de ccxt.

        Args:
            symbol: Paire de trading (ex: 'BTC/USD')
            timeframe: Timeframe (ex: '1m', '5m', '1h', '6h', '1d')
            limit: Nombre de bougies à récupérer (max 300)

        Returns:
            list: Liste des bougies OHLCV

        Raises:
            Exception: En cas d'erreur lors de la récupération
        """
        try:
            # Conversion du symbole au format Coinbase (ex: ETH/USD -> ETH-USD)
            symbol = symbol.replace("/", "-")

            # Conversion du timeframe en chaîne de caractères pour éviter les erreurs
            timeframe_str = str(timeframe)

            # Limiter à 300 bougies maximum
            limit = min(limit, 300)

            # Pour Coinbase, utiliser directement les timeframes standards de ccxt
            # Coinbase dans ccxt a été mis à jour pour utiliser les timeframes standards
            # Mais il faut s'assurer que le timeframe est une chaîne de caractères
            timeframe_str = str(timeframe)

            # Utiliser la méthode standard de ccxt avec le timeframe en chaîne
            ohlcv = cast(
                List[List[Any]],
                self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe_str,  # Timeframe en chaîne de caractères
                    limit=limit,
                ),
            )
            return ohlcv

        except Exception as e:
            logger.error(
                f"Échec de la récupération des OHLCV Coinbase pour {symbol} ({timeframe}): {e}"
            )
            raise
