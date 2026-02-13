"""
Client pour l'exchange Kraken.
Ce module fournit une interface pour interagir avec l'API Kraken. Pas besoin de clef API puor les données publiques sur Kraken.
"""

import ccxt
from logger_settings import logger


class KrakenClient:
    """
    Client pour interagir avec l'API Kraken. Pour les données de marché publiques, aucune clé API n'est nécessaire.

    Attributes:
        exchange: Instance ccxt de l'exchange Kraken
    """

    def __init__(self, use_auth=False, api_key=None, api_secret=None):
        """
        Initialise le client Kraken.

        Args:
            use_auth: Si True, utilise l'authentification (pour le trading)
            api_key: Clé API Kraken (requise si use_auth=True)
            api_secret: Secret API Kraken (requis si use_auth=True)

        Raises:
            ValueError: Si use_auth=True mais les clés API ne sont pas fournies
        """
        if use_auth:
            if not api_key or not api_secret:
                error_msg = "Les clés API Kraken sont requises pour les opérations authentifiées"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Initialisation avec authentification pour le trading
            self.exchange = ccxt.kraken(
                {
                    "apiKey": api_key,
                    "secret": api_secret,
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"},
                }
            )
        else:
            # Initialisation sans authentification pour les données publiques
            self.exchange = ccxt.kraken(
                {
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"},
                }
            )

        # Synchronisation du temps
        self._sync_time()

        # Vérification de l'initialisation
        self._check_exchange_initialization()

    def _sync_time(self):
        """
        Synchro horloge locale avec Kraken.
        """
        try:
            server_time = self.exchange.fetch_time()
            self.exchange.options["timeDifference"] = (
                server_time - self.exchange.milliseconds()
            )
            logger.info("Synchro de l'heure Kraken réussie")
        except Exception as e:
            logger.warning(f"Échec de la synchro de l'heure Kraken: {e}")

    def _check_exchange_initialization(self):
        """
        Vérifie que l'exchange Kraken est correctement initialisé et accessible.

        Raises:
            RuntimeError: Si l'initialisation échoue
        """
        try:
            # Test simple pour vérifier que l'exchange répond
            self.exchange.fetch_status()
            logger.info("Initialisation de l'exchange Kraken réussie")
        except Exception as e:
            logger.error(f"Échec de la vérification de l'initialisation de Kraken: {e}")
            raise RuntimeError(f"Échec de l'initialisation de l'exchange Kraken: {e}")

    def fetch_ticker(self, symbol: str) -> dict:
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
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(
                f"Échec de la récupération du ticker Kraken pour {symbol}: {e}"
            )
            raise

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        """
        Récupère les données OHLCV pour une paire.

        Args:
            symbol: Paire de trading (ex: 'BTC/USD')
            timeframe: Timeframe (ex: '1h', '4h', '1d')
            limit: Nombre de bougies à récupérer

        Returns:
            list: Liste des bougies OHLCV

        Raises:
            Exception: En cas d'erreur lors de la récupération
        """
        try:
            return self.exchange.fetch_ohlcv(
                symbol=symbol, timeframe=timeframe, limit=limit
            )
        except Exception as e:
            logger.error(
                f"Échec de la récupération des OHLCV Kraken pour {symbol} ({timeframe}): {e}"
            )
            raise

    def fetch_top_cryptos_by_volume(
        self, limit: int = 50, quote: str = "USDT", show_errors: bool = False
    ) -> list[dict]:
        """
        Récupère les cryptomonnaies les plus échangées (par volume) sur Kraken.
        """
        try:
            logger.info(
                f"Récupération des tickers sur Kraken pour le Top {limit} par volume en {quote}..."
            )

            tickers = self.exchange.fetch_tickers()

            # Stocker les erreurs dans l'instance
            self.error_logs = {
                "missing_price": [],
                "missing_volume": [],
                "conversion_errors": [],
            }

            filtered_tickers = []

            for symbol, ticker in tickers.items():
                if symbol.endswith(f"/{quote}"):

                    last_price = ticker.get("last")
                    if last_price is None:
                        self.error_logs["missing_price"].append(symbol)
                        continue

                    volume = ticker.get("quoteVolume")
                    if volume is None:
                        self.error_logs["missing_volume"].append(symbol)
                        continue

                    try:
                        filtered_tickers.append(
                            {
                                "symbol": symbol,
                                "base": symbol.split("/")[0],
                                "quote": quote,
                                "volume": float(volume),
                                "last_price": float(last_price),
                                "info": ticker,
                            }
                        )
                    except (ValueError, TypeError):
                        self.error_logs["conversion_errors"].append(symbol)
                        continue

            total_errors = sum(len(v) for v in self.error_logs.values())
            if total_errors > 0:
                logger.warning(
                    f"{total_errors} tickers avec données invalides. "
                    f"Utilisez client.show_ticker_errors() pour les détails."
                )

            if not filtered_tickers:
                logger.warning(f"Aucune paire valide trouvée en {quote}.")
                return []

            sorted_tickers = sorted(
                filtered_tickers, key=lambda x: x["volume"], reverse=True
            )

            result = sorted_tickers[:limit]

            logger.info(f"Top {len(result)} cryptos récupéré avec succès.")

            if show_errors:
                self.show_ticker_errors()

            return result

        except Exception as e:
            logger.error(f"Erreur dans fetch_top_cryptos_by_volume: {e}", exc_info=True)
            raise

    def show_ticker_errors(self):
        """Affiche les erreurs détaillées des tickers."""
        if hasattr(self, "error_logs") and self.error_logs:
            for error_type, symbols in self.error_logs.items():
                if symbols:
                    logger.warning(
                        f"{error_type.replace('_', ' ').title()}: "
                        f"{', '.join(symbols)}"
                    )
        else:
            logger.warning("Aucune erreur enregistrée.")
