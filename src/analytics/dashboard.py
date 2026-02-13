import pandas as pd
import logging
from typing import Optional
from src.analytics.db_inspector import DBInspector
from src.analytics.plot_manager import PlotManager
from src.analytics.technical_calculator import calculate_sma, calculate_rsi


class Dashboard:
    """
    Classe pour visualiser les données financières (OHLCV, SMA, etc.) dans un notebook.
    Permet de récupérer les données, inspecter la base, et tracer les graphiques.
    """

    def __init__(self):
        """Initialise le dashboard avec les outils nécessaires."""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.db_inspector = DBInspector()
        self.plot_manager = PlotManager()
        self.global_data: Optional[pd.DataFrame] = None
        self.crypto_data: Optional[pd.DataFrame] = None

    def fetch_data(self, symbol: str = "BTC/USDT", limit: int = 100) -> None:
        """
        Récupère les données OHLCV depuis la base de données.

        Args:
            symbol: Symbole à récupérer (ex: "BTC/USDT").
            limit: Nombre de lignes à récupérer.
        """
        try:
            self.logger.info(f"Récupération des données OHLCV pour {symbol}...")
            self.global_data = self.db_inspector.get_ohlcv_data()
            self.crypto_data = self.db_inspector.get_ohlcv_data(
                symbol=symbol, limit=limit
            )

            if self.crypto_data is not None and not self.crypto_data.empty:
                display(self.crypto_data.head())
                self.logger.info("Données OHLCV récupérées avec succès.")
            else:
                self.logger.warning(
                    "Aucune donnée OHLCV récupérée. Vérifie la requête ou la base de données."
                )
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des données OHLCV : {e}")

    def inspect_db(self) -> None:
        """Inspecte la base de données et affiche les informations."""
        try:
            self.logger.info("Inspection de la base de données...")
            self.db_inspector.inspect_db()
            self.logger.info("Inspection terminée.")
        except Exception as e:
            self.logger.error(
                f"Erreur lors de l'inspection de la base de données : {e}"
            )

    def show_tables(self) -> None:
        """Affiche les noms des tables disponibles dans la base."""
        try:
            self.logger.info("Récupération des noms des tables...")
            tables = self.db_inspector.get_table_names()
            self.logger.info(f"Tables disponibles : {tables}")
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la récupération des noms des tables : {e}"
            )

    def show_schema(self, table_name: str = "ohlcv") -> None:
        """
        Affiche le schéma d'une table spécifique.

        Args:
            table_name: Nom de la table (ex: "ohlcv").
        """
        try:
            self.logger.info(f"Récupération du schéma de la table '{table_name}'...")
            schema = self.db_inspector.get_table_schema(table_name)
            self.logger.info(f"Schéma de la table '{table_name}' : {schema}")
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la récupération du schéma de la table '{table_name}' : {e}"
            )

    def plot_ohlcv(self, title: str = "BTC/USDT - Données OHLCV") -> None:
        """
        Trace le graphique OHLCV pour les données BTC/USDT.

        Args:
            title: Titre du graphique.
        """
        if self.crypto_data is not None and not self.crypto_data.empty:
            try:
                self.logger.info(f"Tracé du graphique OHLCV : {title}")
                self.plot_manager.plot_ohlcv(self.crypto_data, title=title)
            except Exception as e:
                self.logger.error(f"Erreur lors du traçage OHLCV : {e}")
        else:
            self.logger.warning(
                "Impossible de tracer le graphique OHLCV : les données ne sont pas disponibles."
            )

    def plot_sma(
        self, window: int = 20, title: str = "BTC/USDT - Prix avec SMA (20)"
    ) -> None:
        """
        Calcule et trace la SMA pour les données BTC/USDT.

        Args:
            window: Période de la SMA.
            title: Titre du graphique.
        """
        if self.crypto_data is not None and not self.crypto_data.empty:
            try:
                self.logger.info(
                    f"Calcul de la SMA pour BTC/USDT (fenêtre: {window})..."
                )
                sma_serie = calculate_sma(self.crypto_data)
                self.plot_manager.plot_with_sma(
                    self.crypto_data, sma_serie, window=window, title=title
                )
            except Exception as e:
                self.logger.error(
                    f"Erreur lors du calcul ou du traçage de la SMA : {e}"
                )
        else:
            self.logger.warning(
                "Impossible de calculer la SMA : les données ne sont pas disponibles."
            )

    def plot_rsi(
        self,
        window: int = 20,
        title: str = "BTC/USDT - RSI (14)",
        price_column: str = "close",
    ) -> None:
        """
        Calcule et trace le RSI pour les données BTC/USDT.

        Args:
            window: Période pour le calcul du RSI (par défaut 14).
            title: Titre du graphique.
            price_column: Nom de la colonne de prix (par défaut 'close').
        """
        if self.crypto_data is not None and not self.crypto_data.empty:
            try:
                self.logger.info(f"Calcul du RSI pour BTC/USDT (fenêtre: {window})...")
                rsi_serie = calculate_rsi(
                    self.crypto_data,
                    window=window,
                    price_column=price_column,
                )
                self.plot_manager.plot_rsi(
                    self.crypto_data,
                    rsi_serie,
                    window=window,
                    title=title,
                    price_column=price_column,
                )
            except Exception as e:
                self.logger.error(f"Erreur lors du calcul ou du traçage du RSI : {e}")
        else:
            self.logger.warning(
                "Impossible de calculer le RSI : les données ne sont pas disponibles."
            )

    def plot_prices_evolution(self, symbol: str = "BTC/USDT") -> None:
        """
        Trace l'évolution des prix pour un symbole donné.

        Args:
            symbol: Symbole à tracer (ex: "BTC/USDT").
        """
        if self.global_data is not None and not self.global_data.empty:
            try:
                self.logger.info(f"Tracé de l'évolution des prix pour {symbol}...")
                self.plot_manager.plot_prices_evolution(self.global_data, symbol=symbol)
            except Exception as e:
                self.logger.error(
                    f"Erreur lors du traçage de l'évolution des prix : {e}"
                )
        else:
            self.logger.warning(
                "Impossible de tracer l'évolution des prix : les données ne sont pas disponibles."
            )

    def plot_prices_variations_distrib(self) -> None:
        """Trace la distribution des variations de prix."""
        if self.global_data is not None and not self.global_data.empty:
            try:
                self.logger.info("Tracé de la distribution des variations de prix...")
                self.plot_manager.plot_prices_variations_distrib(self.global_data)
            except Exception as e:
                self.logger.error(
                    f"Erreur lors du traçage de la distribution des variations de prix : {e}"
                )
        else:
            self.logger.warning(
                "Impossible de tracer la distribution des variations de prix : les données ne sont pas disponibles."
            )

    def plot_symbols_volumes(self) -> None:
        """Trace la distribution des volumes par symbole."""
        if self.global_data is not None and not self.global_data.empty:
            try:
                self.logger.info("Tracé des volumes par symbole...")
                self.plot_manager.plot_symbols_volumes(self.global_data)
            except Exception as e:
                self.logger.error(f"Erreur lors du traçage des volumes : {e}")
        else:
            self.logger.warning(
                "Impossible de tracer les volumes : les données ne sont pas disponibles."
            )

    def run(self, symbol: str = "BTC/USDT", limit: int = 100) -> None:
        """
        Exécute le dashboard complet : récupère les données, inspecte la base, et trace les graphiques.

        Args:
            symbol: Symbole à analyser (ex: "BTC/USDT").
            limit: Nombre de lignes à récupérer.
        """
        self.fetch_data(symbol=symbol, limit=limit)
        self.inspect_db()
        self.show_tables()
        self.show_schema()
        self.plot_ohlcv()
        self.plot_sma()
        self.plot_rsi()
        self.plot_prices_evolution()
        self.plot_prices_variations_distrib()
        self.plot_symbols_volumes()
