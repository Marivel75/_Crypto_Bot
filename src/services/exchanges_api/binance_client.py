"""
Client pour l'exchange Binance.
Ce module fournit une interface pour interagir avec l'API Binance.
"""

import ccxt
from logger_settings import logger
from src.config.settings import BINANCE_API_KEY, BINANCE_API_SECRET


class BinanceClient:
    def __init__(self):
        # Validation des clés API avant initialisation
        self._validate_api_keys()

        self.exchange = ccxt.binance(
            {
                "apiKey": BINANCE_API_KEY,
                "secret": BINANCE_API_SECRET,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )

        # Fonction privée pour synchroniser l'heure locale avec l'heure serveur de Binance
        self._sync_time()

        # Vérification que l'échange est correctement initialisé
        self._check_exchange_initialization()

    def _sync_time(self):
        """
        Synchronisation horloge locale avec Binance
        """
        try:
            server_time = self.exchange.fetch_time()
            self.exchange.options["timeDifference"] = (
                server_time - self.exchange.milliseconds()
            )
            logger.info("Synchro de l'heure Binance réussie")
        except Exception as e:
            logger.warning(f"Échec de la synchro de l'heure: {e}")

    def _validate_api_keys(self):
        """
        Valide que les clés API sont définies avant d'initialiser l'échange
        """
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            error_msg = "La clé API Binance ou le secret n'est pas configuré"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(BINANCE_API_KEY, str) or not isinstance(
            BINANCE_API_SECRET, str
        ):
            error_msg = "La clé API Binance et le secret doivent être des chaînes de caractères (str)"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not BINANCE_API_KEY.strip() or not BINANCE_API_SECRET.strip():
            error_msg = "La clé API Binance ou le secret est vide"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _check_exchange_initialization(self):
        """
        Vérifie que l'exchange est correctement initialisé et accessible
        """
        try:
            # Test simple pour vérifier que l'échange répond
            self.exchange.fetch_status()
            logger.info("Initialisation de l'exchange réussie")
        except Exception as e:
            logger.error(
                f"Échec de la vérification de l'initialisation de l'exchange: {e}"
            )
            raise RuntimeError(f"Échec de l'initialisation de l'exchange Binance: {e}")

    def fetch_ticker(self, symbol: str) -> dict:
        """
        Méthode ccxt de la classe Exchange pour récupérer le ticker d'une paire (résumé rapide de l’état actuel du marché pour une paire de trading).
        Récupère le dernier prix et infos marché pour une paire (BTC/USDT, ETH/USDT, etc.), renvoie un dictionnaire contenant :
        - last (dernier prix)
        high / low / open
        - volume
        - bid / ask
        - timestamp

        Returns:
            dict: Informations du ticker

        Raises:
            Exception: En cas d'erreur lors de la récupération du ticker
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Échec de la récupération du ticker pour {symbol}: {e}")
            raise

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        """
        Méthode ccxt de la classe Exchange
        Récupère les bougies OHLCV (Open, High, Low, Close, Volume)
        timeframe : "1m", "5m", "1h", "1d", etc.
        limit : nombre de bougies à récupérer
        Retourne une liste de listes

        Returns:
            list: Liste des bougies OHLCV

        Raises:
            Exception: En cas d'erreur lors de la récupération des données OHLCV
        """
        try:
            return self.exchange.fetch_ohlcv(
                symbol=symbol, timeframe=timeframe, limit=limit
            )
        except Exception as e:
            logger.error(
                f"Échec de la récupération des OHLCV pour {symbol} avec timeframe {timeframe}: {e}"
            )
            raise

    def fetch_top_cryptos_by_volume(
        self, limit: int = 50, quote: str = "USDT"
    ) -> list[dict]:
        """
        Récupère les cryptomonnaies les plus échangées (par volume) sur Binance.

        Args:
            limit: Nombre de cryptos à retourner (default 50).
            quote: Devise de cotation (ex. "USDT", "BUSD", "BTC").

        Returns:
            list[dict]: Liste des cryptos triées par volume décroissant.
        """
        try:
            logger.info(
                f"Récupération des tickers pour le Top {limit} par volume en {quote}..."
            )

            # Récupérer tous les tickers
            tickers = self.exchange.fetch_tickers()

            # Dictionnaire pour stocker les erreurs
            error_logs = {
                "missing_price": [],
                "missing_volume": [],
                "conversion_errors": [],
            }

            # Filtrer les paires en {quote} et extraire les infos utiles
            filtered_tickers = []
            for symbol, ticker in tickers.items():
                if symbol.endswith(f"/{quote}"):
                    try:
                        last_price = ticker.get("last")
                        if last_price is None:
                            error_logs["missing_price"].append(symbol)
                            continue

                        volume = ticker.get("quoteVolume")
                        if volume is None:
                            error_logs["missing_volume"].append(symbol)
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
                        except (ValueError, TypeError) as e:
                            error_logs["conversion_errors"].append(symbol)
                            continue

                    except Exception as e:
                        error_logs["conversion_errors"].append(symbol)
                        continue

            # Log général des erreurs
            total_errors = sum(len(errors) for errors in error_logs.values())
            if total_errors > 0:
                logger.warning(
                    f"Absence de données valides pour {total_errors} tickers. "
                    f"Tapez 'client.show_ticker_errors()' pour consulter les logs détaillés."
                )

            if not filtered_tickers:
                logger.warning(f"Aucune paire valide trouvée en {quote}.")
                return []

            # Trier par volume décroissant
            sorted_tickers = sorted(
                filtered_tickers, key=lambda x: x["volume"], reverse=True
            )

            # Limiter au nombre demandé
            result = sorted_tickers[:limit]
            logger.info(f"Top {len(result)} cryptos par volume récupéré avec succès.")
            return result

        except Exception as e:
            logger.error(f"Erreur dans fetch_top_cryptos_by_volume: {e}", exc_info=True)
            raise

        # Méthode pour afficher les erreurs détaillées
        def show_ticker_errors(self):
            """Affiche les erreurs détaillées des tickers."""
            if hasattr(self, "error_logs") and self.error_logs:
                for error_type, symbols in self.error_logs.items():
                    if symbols:
                        logger.warning(
                            f"{error_type.replace('_', ' ').title()}: {', '.join(symbols)}"
                        )
            else:
                logger.warning("Aucune erreur enregistrée.")
