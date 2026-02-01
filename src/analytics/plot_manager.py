"""
Module pour gérer la visualisation des données financières (OHLCV, SMA, etc.).
Utilise mplfinance pour générer des graphiques de type TradingView.
Compatible avec les environnements de développement et de production.
"""

import mplfinance as mpf
import pandas as pd
from typing import Optional, Dict, Any, List, Union
from logger_settings import logger
from src.models.ohlcv import OHLCV
from src.config.settings import ENVIRONMENT


class PlotManager:
    """
    Classe pour gérer la visualisation des données financières.
    Permet de tracer des graphiques OHLCV avec des indicateurs (SMA, etc.).
    """

    def __init__(self):
        """Initialise le gestionnaire de visualisation."""
        logger.info(f"Initialisation de PlotManager (Environnement: {ENVIRONMENT})")

    def _prepare_data_for_plot(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prépare les données pour le plot en utilisant OHLCV.prepare_for_mplfinance
        et en vérifiant que l'index est un DatetimeIndex.

        Args:
            data: DataFrame avec les données OHLCV.

        Returns:
            DataFrame prêt pour mplfinance.
        """
        logger.debug(
            f"Préparation des données pour le plot (Environnement: {ENVIRONMENT})"
        )

        # Préparer les données avec la méthode de la classe OHLCV
        data = OHLCV.prepare_for_mplfinance(data)

        # Vérifier que l'index est un DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            if "timestamp" in data.columns:
                data = data.set_index("timestamp")
            data.index = pd.to_datetime(data.index)

        logger.debug(f"Données préparées avec succès (Environnement: {ENVIRONMENT})")
        return data

    def plot_ohlcv(
        self,
        data: pd.DataFrame,
        title: str = "Prix OHLCV",
        style: str = "binance",
        volume: bool = True,
        save_path: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        """
        Trace un graphique OHLCV de base.

        Args:
            data: DataFrame avec colonnes OHLCV (open, high, low, close, volume).
            title: Titre du graphique.
            style: Style de mplfinance (ex: 'binance', 'charles', 'yahoo').
            volume: Si True, affiche le volume.
            save_path: Chemin pour sauvegarder le graphique (optionnel).
            **kwargs: Arguments supplémentaires pour mpf.plot().
        """
        logger.info(
            f"Tracé du graphique OHLCV : {title} (Environnement: {ENVIRONMENT})"
        )

        try:
            # Préparer les données
            data = self._prepare_data_for_plot(data)

            # Configuration par défaut
            plot_kwargs = {
                "type": "candle",
                "title": title,
                "style": style,
                "volume": volume,
                "ylabel": "Prix",
                "ylabel_lower": "Volume",
                "figratio": (12, 8),
                "figscale": 1.1,
                "returnfig": True,
                "savefig": save_path if save_path else None,
            }
            plot_kwargs.update(kwargs)  # Fusion avec les kwargs utilisateur

            # Tracer le graphique
            fig, axes = mpf.plot(data, **plot_kwargs)

            if save_path:
                logger.info(
                    f"Graphique sauvegardé à {save_path} (Environnement: {ENVIRONMENT})"
                )

        except Exception as e:
            logger.error(
                f"❌ Erreur lors du traçage OHLCV (Environnement: {ENVIRONMENT}): {e}"
            )
            raise

    def plot_with_sma(
        self,
        data: pd.DataFrame,
        sma_data: pd.Series,
        window: int = 20,
        title: str = "Prix avec SMA",
        style: str = "binance",
        save_path: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        """
        Trace un graphique OHLCV avec une SMA.

        Args:
            data: DataFrame avec colonnes OHLCV (open, high, low, close, volume).
            sma_data: Série pandas contenant les valeurs SMA (calculées par calculate_sma).
            window: Période de la SMA (par défaut 20).
            title: Titre du graphique.
            style: Style de mplfinance.
            save_path: Chemin pour sauvegarder le graphique (optionnel).
            **kwargs: Arguments supplémentaires pour mpf.plot().
        """
        logger.info(
            f"Tracé du graphique avec SMA (fenêtre: {window}) (Environnement: {ENVIRONMENT})"
        )

        try:
            # Préparer les données
            data = self._prepare_data_for_plot(data)

            # Ajouter la série SMA au DataFrame
            data[f"SMA_{window}"] = sma_data

            # Configuration par défaut
            plot_kwargs = {
                "type": "candle",
                "title": title,
                "style": style,
                "mav": (window,),
                "volume": True,
                "ylabel": "Prix",
                "ylabel_lower": "Volume",
                "figratio": (12, 8),
                "figscale": 1.1,
                "returnfig": True,
                "savefig": save_path if save_path else None,
            }
            plot_kwargs.update(kwargs)

            # Tracer le graphique
            fig, axes = mpf.plot(data, **plot_kwargs)

            if save_path:
                logger.info(
                    f"Graphique avec SMA sauvegardé à {save_path} (Environnement: {ENVIRONMENT})"
                )

        except Exception as e:
            logger.error(
                f"❌ Erreur lors du traçage avec SMA (Environnement: {ENVIRONMENT}): {e}"
            )
            raise

    def plot_multiple_indicators(
        self,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series],
        title: str = "Prix avec indicateurs",
        style: str = "binance",
        save_path: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        """
        Trace un graphique OHLCV avec plusieurs indicateurs.

        Args:
            data: DataFrame avec colonnes OHLCV.
            indicators: Dictionnaire d'indicateurs {nom: série}.
            title: Titre du graphique.
            style: Style de mplfinance.
            save_path: Chemin pour sauvegarder le graphique (optionnel).
            **kwargs: Arguments supplémentaires pour mpf.plot().
        """
        logger.info(
            f"Tracé du graphique avec plusieurs indicateurs (Environnement: {ENVIRONMENT})"
        )

        try:
            # Préparer les données
            data = self._prepare_data_for_plot(data)

            # Ajouter les indicateurs au DataFrame
            for name, series in indicators.items():
                data[name] = series

            # Configuration par défaut
            plot_kwargs = {
                "type": "candle",
                "title": title,
                "style": style,
                "volume": True,
                "ylabel": "Prix",
                "ylabel_lower": "Volume",
                "figratio": (12, 8),
                "figscale": 1.1,
                "returnfig": True,
                "savefig": save_path if save_path else None,
            }

            # Ajouter les indicateurs à afficher
            if "mav" not in plot_kwargs:
                plot_kwargs["mav"] = ()

            # Tracer le graphique
            fig, axes = mpf.plot(data, **plot_kwargs)

            if save_path:
                logger.info(
                    f"Graphique avec indicateurs sauvegardé à {save_path} (Environnement: {ENVIRONMENT})"
                )

        except Exception as e:
            logger.error(
                f"❌ Erreur lors du traçage avec indicateurs (Environnement: {ENVIRONMENT}): {e}"
            )
            raise
