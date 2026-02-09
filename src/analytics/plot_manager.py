"""
Module pour gérer la visualisation des données financières (OHLCV, SMA, etc.).
Utilise mplfinance pour générer des graphiques de type TradingView.
"""

import mplfinance as mpf
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Optional, Dict, Any, List, Union
from logger_settings import logger
from src.models.ohlcv import OHLCV


class PlotManager:
    """
    Classe pour gérer la visualisation des données financières.
    Permet de tracer des graphiques OHLCV avec des indicateurs (SMA, etc.).
    """

    def __init__(self):
        """Initialise le gestionnaire de visualisation et configure les styles globaux."""
        logger.debug("Initialisation de PlotManager")
        self._set_global_styles()
        self._default_plot_kwargs = {
            "type": "candle",
            "ylabel": "Prix",
            "ylabel_lower": "Volume",
            "figratio": (12, 8),
            "figscale": 1.1,
        }

    def _set_global_styles(self) -> None:
        """
        Configure les styles globaux pour matplotlib, seaborn et pandas.
        """
        plt.style.use("seaborn-v0_8-dark")
        sns.set_theme(style="whitegrid")
        pd.set_option("display.max_columns", None)
        logger.debug("Styles globaux configurés.")

    def _prepare_data_for_mplfinance(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prépare les données pour le plot en utilisant OHLCV.prepare_for_mplfinance
        et en vérifiant que l'index est un DatetimeIndex.

        Args:
            data: DataFrame avec les données OHLCV.

        Returns:
            DataFrame prêt pour mplfinance.
        """
        data = OHLCV.prepare_for_mplfinance(data)
        if not isinstance(data.index, pd.DatetimeIndex):
            if "timestamp" in data.columns:
                data = data.set_index("timestamp")
            data.index = pd.to_datetime(data.index)
        return data

    def _get_plot_kwargs(
        self, title: str, style: str, volume: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Retourne les arguments de configuration pour mpf.plot.

        Args:
            title: Titre du graphique.
            style: Style de mplfinance.
            volume: Si True, affiche le volume.
            **kwargs: Arguments supplémentaires pour mpf.plot().

        Returns:
            Dictionnaire des arguments pour mpf.plot.
        """
        plot_kwargs = self._default_plot_kwargs.copy()
        plot_kwargs.update(
            {
                "title": title,
                "style": style,
                "volume": volume,
            }
        )
        plot_kwargs.update(kwargs)
        return plot_kwargs

    def _plot_with_mplfinance(self, data: pd.DataFrame, **plot_kwargs) -> None:
        """
        Trace un graphique avec mplfinance.

        Args:
            data: DataFrame avec colonnes OHLCV.
            **plot_kwargs: Arguments pour mpf.plot().
        """
        try:
            mpf.plot(data, **plot_kwargs)
        except Exception as e:
            logger.error(f"❌ Erreur lors du traçage: {e}")
            raise

    def plot_ohlcv(
        self,
        data: pd.DataFrame,
        title: str = "Prix OHLCV",
        style: str = "binance",
        volume: bool = True,
        **kwargs: Dict[str, Any],
    ) -> None:
        """
        Trace un graphique OHLCV de base.

        Args:
            data: DataFrame avec colonnes OHLCV.
            title: Titre du graphique.
            style: Style de mplfinance.
            volume: Si True, affiche le volume.
            **kwargs: Arguments supplémentaires pour mpf.plot().
        """
        logger.info(f"Tracé du graphique OHLCV : {title}")
        data = self._prepare_data_for_mplfinance(data)
        plot_kwargs = self._get_plot_kwargs(title, style, volume, **kwargs)
        self._plot_with_mplfinance(data, **plot_kwargs)

    def plot_with_sma(
        self,
        data: pd.DataFrame,
        sma_data: pd.Series,
        window: int = 20,
        title: str = "Prix avec SMA",
        style: str = "binance",
        **kwargs: Dict[str, Any],
    ) -> None:
        """
        Trace un graphique OHLCV avec une SMA.

        Args:
            data: DataFrame avec colonnes OHLCV.
            sma_data: Série pandas contenant les valeurs SMA.
            window: Période de la SMA.
            title: Titre du graphique.
            style: Style de mplfinance.
            **kwargs: Arguments supplémentaires pour mpf.plot().
        """
        logger.info(f"Tracé du graphique avec SMA (fenêtre: {window})")
        data = self._prepare_data_for_mplfinance(data)
        data[f"SMA_{window}"] = sma_data
        plot_kwargs = self._get_plot_kwargs(title, style, **kwargs)
        plot_kwargs["mav"] = (window,)
        self._plot_with_mplfinance(data, **plot_kwargs)

    def plot_prices_evolution(
        self, data: pd.DataFrame, symbol: str = "BTC/USDT"
    ) -> None:
        """
        Trace l'évolution des prix pour un symbole donné.

        Args:
            data: DataFrame avec colonnes OHLCV.
            symbol: Symbole à tracer.
        """
        if "timestamp" in data.columns:
            data = data.set_index("timestamp")
        data.index = pd.to_datetime(data.index)
        df_symbol = data[data["symbol"] == symbol].sort_index()

        plt.figure(figsize=(8, 3))
        plt.plot(df_symbol.index, df_symbol["close"], label="Prix", color="blue")
        plt.title(f"Évolution du prix {symbol}", fontsize=16)
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Prix (USD)", fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def plot_prices_variations_distrib(self, data: pd.DataFrame) -> None:
        """
        Trace la distribution des variations de prix.

        Args:
            data: DataFrame avec colonnes OHLCV.
        """
        if "timestamp" in data.columns:
            data = data.set_index("timestamp")
        data.index = pd.to_datetime(data.index)

        plt.figure(figsize=(8, 3))
        sns.histplot(data=data, x="price_change_pct", hue="symbol", kde=True, bins=50)
        plt.title("Distribution des variations de prix (%)", fontsize=16)
        plt.xlabel("Variation de prix (%)", fontsize=12)
        plt.ylabel("Fréquence", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.show()

    def plot_symbols_volumes(self, data: pd.DataFrame) -> None:
        """
        Trace la distribution des volumes par symbole.

        Args:
            data: DataFrame avec colonnes OHLCV.
        """
        if "timestamp" in data.columns:
            data = data.set_index("timestamp")
        data.index = pd.to_datetime(data.index)

        plt.figure(figsize=(8, 6))
        sns.boxplot(data=data, x="symbol", y="volume")
        plt.title("Distribution des volumes par symbole", fontsize=16)
        plt.xlabel("Symbole", fontsize=12)
        plt.ylabel("Volume", fontsize=12)
        plt.yscale("log")
        plt.grid(True, alpha=0.3)
        plt.show()
