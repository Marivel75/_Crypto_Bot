"""
Module pour gérer la visualisation des données financières (OHLCV, SMA, etc.).
Utilise mplfinance pour générer des graphiques de type TradingView.
"""

import mplfinance as mpf
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Optional, Dict, Any, List
from logger_settings import logger
from src.analytics.technical_calculator import TechnicalCalculator


class PlotManager:
    """
    Classe pour gérer la visualisation des données financières.
    Permet de tracer des graphiques OHLCV avec des indicateurs (SMA, RSI, etc.).
    """

    MAX_CANDLES = 500  # Limite maximale de bougies pour garantir la lisibilité

    def __init__(self):
        """Initialise le gestionnaire de visualisation et configure les styles globaux."""
        logger.debug("Initialisation de PlotManager")
        self._set_global_styles()
        self.mplfinance_style = "binance"
        self.default_plot_kwargs = {
            "type": "candle",
            "ylabel": "Prix",
            "ylabel_lower": "Volume",
            "figratio": (12, 8),
            "figscale": 1.1,
            "warn_too_much_data": self.MAX_CANDLES + 100,
            "style": self.mplfinance_style,
        }

    def _set_global_styles(self) -> None:
        """Configure les styles globaux pour matplotlib, seaborn et pandas."""
        plt.style.use("seaborn-v0_8-dark")
        sns.set_theme(style="whitegrid")
        pd.set_option("display.max_columns", None)
        logger.debug("Styles globaux configurés.")

    def _validate_data_length(
        self, data: pd.DataFrame, limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Valide que le nombre de bougies ne dépasse pas la limite spécifiée (ou MAX_CANDLES).
        Tronque les données si nécessaire et log un warning.

        Args:
            data: DataFrame avec les données OHLCV.
            limit: Limite personnalisée (optionnelle). Si None, utilise MAX_CANDLES.

        Returns:
            DataFrame: Données tronquées si nécessaire.
        """
        max_limit = limit if limit is not None else self.MAX_CANDLES

        if len(data) > max_limit:
            logger.warning(
                f"Trop de données à tracer ({len(data)} bougies). "
                f"Seules les {max_limit} dernières seront affichées pour garantir la lisibilité."
            )
            data = data.iloc[-max_limit:]
            if data.empty:
                raise ValueError("Aucune donnée valide après troncature.")

        return data

    def _prepare_data_for_mplfinance(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prépare les données pour mplfinance en vérifiant les colonnes et l'index.
        """
        prepared_data = data.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            errors="ignore",
        )
        if not isinstance(prepared_data.index, pd.DatetimeIndex):
            if "timestamp" in prepared_data.columns:
                prepared_data = prepared_data.set_index("timestamp")
            prepared_data.index = pd.to_datetime(prepared_data.index)
        return prepared_data

    def plot_ohlcv(
        self, data: pd.DataFrame, limit: Optional[int] = None, plot_type: str = "candle"
    ) -> None:
        """
        Trace un graphique OHLCV avec une limite personnalisable de bougies.

        Args:
            data: DataFrame avec les données OHLCV.
            limit: Limite personnalisée du nombre de bougies (optionnelle).
                   Si None, utilise MAX_CANDLES.
            plot_type: Type de graphique ('candle', 'line', etc.).
        """
        logger.info(f"Tracé du graphique OHLCV (type: {plot_type})")
        data = self._validate_data_length(data, limit)  # Applique la limite
        data = self._prepare_data_for_mplfinance(data)

        mpf.plot(
            data,
            **self.default_plot_kwargs,
            volume=True,
        )

    def plot_rsi(
        self,
        data: pd.DataFrame,
        rsi_serie: Optional[pd.Series] = None,
        window: int = 14,
        title: str = "Prix avec RSI",
        limit: Optional[int] = None,
        price_column: str = "close",
    ) -> None:
        """
        Version simplifiée pour garantir la cohérence.
        """
        logger.info(f"Tracé du graphique avec RSI (fenêtre: {window})")

        # 1. Tronquer à une limite suffisante pour calculer le RSI
        if limit is None:
            limit = self.MAX_CANDLES

        # S'assurer d'avoir assez de données pour le RSI
        min_limit = max(limit, window + 50)
        if len(data) > min_limit:
            data = data.iloc[-min_limit:]
        elif len(data) < window + 10:
            raise ValueError(
                f"Besoin d'au moins {window + 10} bougies pour calculer le RSI"
            )

        # 2. Calculer le RSI sur toutes les données disponibles
        calculator = TechnicalCalculator()
        all_rsi = calculator.calculate_rsi(
            data, window=window, price_column=price_column
        )

        if isinstance(all_rsi, list):
            all_rsi = pd.Series(all_rsi, index=data.index[-len(all_rsi) :])

        # 3. Tronquer pour l'affichage final
        display_data = data.iloc[-limit:] if len(data) > limit else data
        display_rsi = all_rsi.iloc[-len(display_data) :]

        # 4. Préparer les données
        plot_data = self._prepare_data_for_mplfinance(display_data)

        # 5. Tracer
        addplots = [
            mpf.make_addplot(display_rsi, panel=1, color="purple", ylabel="RSI"),
            mpf.make_addplot(
                [70] * len(display_rsi), panel=1, color="red", linestyle="--"
            ),
            mpf.make_addplot(
                [30] * len(display_rsi), panel=1, color="green", linestyle="--"
            ),
        ]

        mpf.plot(
            plot_data,
            type="candle",
            volume=True,
            addplot=addplots,
            panel_ratios=(3, 1),
            title=title,
            style=self.mplfinance_style,
            figratio=(12, 8),
        )

    def plot_sma(
        self,
        data: pd.DataFrame,
        sma_serie: Optional[pd.Series] = None,
        window: int = 20,
        title: str = "Prix avec SMA",
        limit: Optional[int] = None,
        price_column: str = "close",
        sma_color: str = "orange",
        line_width: float = 1.5,
    ) -> None:
        """
        Trace un graphique OHLCV avec une Simple Moving Average (SMA).
        """
        logger.info(f"Tracé du graphique avec SMA, window : {window}")

        if data.empty:
            raise ValueError("Données vides")

        # 1. Garder une copie des données originales pour référence
        original_data = data.copy()

        # 2. Calculer la SMA sur toutes les données d'abord
        if sma_serie is None:
            prices = (
                original_data[price_column]
                if price_column in original_data.columns
                else original_data["close"]
            )
            # Calculer la SMA sur toutes les données
            sma_all = prices.rolling(window=window).mean()
        else:
            sma_all = sma_serie

        # 3. Appliquer la limite après le calcul de la SMA
        if limit and len(original_data) > limit:
            data = original_data.iloc[-limit:]
            # Prendre aussi la SMA correspondante
            sma_to_plot = sma_all.loc[data.index]
        else:
            data = original_data
            sma_to_plot = sma_all

        # 4. Supprimer les NaN de la SMA
        sma_clean = sma_to_plot.dropna()
        if sma_clean.empty:
            logger.warning(f"SMA{window} vide - affichage sans SMA")
            self.plot_ohlcv(data, limit=limit)
            return

        # 5. S'assurer que les données et la SMA ont les mêmes indices
        # Garder seulement les indices communs
        common_idx = data.index.intersection(sma_clean.index)
        if len(common_idx) == 0:
            logger.error(
                f"Aucun index commun entre données ({len(data)}) et SMA ({len(sma_clean)})"
            )
            logger.warning(f"Affichage sans SMA")
            self.plot_ohlcv(data, limit=limit)
            return

        data = data.loc[common_idx]
        sma_final = sma_clean.loc[common_idx]

        logger.debug(
            f"Données finales: {len(data)} points, SMA: {len(sma_final)} points"
        )

        # 6. Préparer les données pour mplfinance
        plot_data = self._prepare_data_for_mplfinance(data)

        # 7. Créer le graphique
        ap = mpf.make_addplot(
            sma_final,
            color=sma_color,
            width=line_width,
            label=f"SMA{window}",
        )

        plot_kwargs = self.default_plot_kwargs.copy()
        plot_kwargs.update(
            {
                "title": f"{title} (window : {window})",
                "addplot": [ap],
                "volume": True,
            }
        )

        try:
            mpf.plot(plot_data, **plot_kwargs)
            logger.info(
                f"Graphique tracé avec succès: {len(data)} bougies, SMA{window}"
            )
        except Exception as e:
            logger.error(f"Erreur lors du tracé: {str(e)}")
            logger.info("Tentative de tracé sans SMA...")
            self.plot_ohlcv(data, limit=limit)
