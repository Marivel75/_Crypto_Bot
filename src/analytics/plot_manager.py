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
        self.calculator = TechnicalCalculator()
        self.mplfinance_style = "binance"
        self.default_plot_kwargs = {
            "type": "candle",
            "ylabel": "Prix",
            "ylabel_lower": "Volume",
            "figratio": (12, 10),
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

    def _calculate_indicator(
        self,
        data: pd.DataFrame,
        indicator_type: str,
        window: int,
        price_column: str = "close",
    ) -> pd.Series:
        """
        Calcule l'indicateur technique en fonction du type.
        """
        if indicator_type.upper() == "SMA":
            return self.calculator.calculate_sma(
                data, window=window, price_column=price_column
            )
        elif indicator_type.upper() == "EMA":
            return self.calculator.calculate_ema(
                data, window=window, price_column=price_column
            )
        elif indicator_type.upper() == "RSI":
            return self.calculator.calculate_rsi(
                data, window=window, price_column=price_column
            )
        else:
            raise ValueError(f"Indicateur non supporté : {indicator_type}")

    def _convert_to_series_and_align(
        self, indicator_data: Optional[pd.Series], data: pd.DataFrame
    ) -> pd.Series:
        """
        Convertit les données d'indicateur en Series si nécessaire et les aligne avec les données.
        """
        if isinstance(indicator_data, list):
            indicator_data = pd.Series(
                indicator_data, index=data.index[-len(indicator_data) :]
            )

        if indicator_data is not None:
            common_idx = data.index.intersection(indicator_data.index)
            if len(common_idx) == 0:
                raise ValueError("Aucun index commun entre les données et l'indicateur")
            return indicator_data.loc[common_idx]

        return indicator_data

    def _apply_limit_and_clean(
        self,
        data: pd.DataFrame,
        indicator_serie: Optional[pd.Series],
        limit: Optional[int],
    ) -> tuple[pd.DataFrame, Optional[pd.Series]]:
        """
        Applique la limite et nettoie les données NaN.
        """
        if limit and len(data) > limit:
            data = data.iloc[-limit:]
            if indicator_serie is not None:
                indicator_serie = indicator_serie.iloc[-limit:]

        if indicator_serie is not None:
            # Supprimer les valeurs NaN
            valid_mask = indicator_serie.notna()
            if not valid_mask.any():
                raise ValueError("L'indicateur ne contient que des valeurs NaN")

            data = data[valid_mask]
            indicator_serie = indicator_serie[valid_mask]

        return data, indicator_serie

    def _create_base_addplot(
        self,
        indicator_serie: pd.Series,
        color: str = "orange",
        label: str = "Indicator",
    ) -> List[Any]:
        """
        Crée un addplot de base pour les indicateurs simples (SMA, EMA).
        """
        return [
            mpf.make_addplot(
                indicator_serie,
                color=color,
                width=1.5,
                label=label,
            )
        ]

    def _create_rsi_addplots(self, rsi_serie: pd.Series, window: int) -> List[Any]:
        """
        Crée les addplots spécifiques pour le RSI.
        """
        return [
            mpf.make_addplot(
                rsi_serie,
                panel=1,
                color="purple",
                ylabel="RSI",
                title=f"RSI({window})",
                width=1.5,
            ),
            mpf.make_addplot(
                [70] * len(rsi_serie),
                panel=1,
                color="red",
                linestyle="--",
                alpha=0.7,
                width=0.8,
            ),
            mpf.make_addplot(
                [30] * len(rsi_serie),
                panel=1,
                color="green",
                linestyle="--",
                alpha=0.7,
                width=0.8,
            ),
        ]

    def _plot_with_indicator(
        self,
        data: pd.DataFrame,
        indicator_name: str,
        indicator_serie: Optional[pd.Series] = None,
        window: int = 20,
        title: str = "Prix avec indicateur",
        limit: Optional[int] = None,
        price_column: str = "close",
        indicator_color: str = "orange",
        **kwargs,
    ) -> None:
        """
        Méthode générique pour tracer un graphique avec un indicateur.
        """
        logger.info(f"Tracé du graphique avec {indicator_name}, window : {window}")

        if data.empty:
            raise ValueError("Données vides")

        # 1. Garder une copie des données originales
        original_data = data.copy()

        # 2. Calculer l'indicateur si non fourni
        if indicator_serie is None:
            indicator_serie = self._calculate_indicator(
                original_data, indicator_name, window, price_column
            )

        # 3. Convertir et aligner l'indicateur
        indicator_serie = self._convert_to_series_and_align(
            indicator_serie, original_data
        )

        # 4. Appliquer la limite et nettoyer
        data, indicator_serie = self._apply_limit_and_clean(
            data, indicator_serie, limit
        )

        if data.empty:
            raise ValueError("Aucune donnée valide après filtrage")

        # 5. Préparer les données pour mplfinance
        plot_data = self._prepare_data_for_mplfinance(data)

        # 6. Créer les addplots selon le type d'indicateur
        if indicator_name.upper() == "RSI":
            addplots = self._create_rsi_addplots(indicator_serie, window)
            panel_ratios = (3, 1)
            main_panel = 0
            volume_panel = 2
        else:
            label = f"{indicator_name}{window}"
            addplots = self._create_base_addplot(
                indicator_serie, indicator_color, label
            )
            panel_ratios = None
            main_panel = None
            volume_panel = None

        # 7. Configurer les paramètres du graphique
        plot_kwargs = self.default_plot_kwargs.copy()
        plot_kwargs.update(
            {
                "title": f"{title} (window : {window})",
                "addplot": addplots,
                "volume": True,
            }
        )

        if indicator_name.upper() == "RSI":
            plot_kwargs["panel_ratios"] = panel_ratios
            plot_kwargs["main_panel"] = main_panel
            plot_kwargs["volume_panel"] = volume_panel

        # 8. Tracer le graphique
        try:
            mpf.plot(plot_data, **plot_kwargs)
            logger.info(
                f"Graphique tracé avec succès: {len(data)} bougies, {indicator_name}{window}"
            )
        except Exception as e:
            logger.error(f"Erreur lors du tracé: {str(e)}")
            # En cas d'erreur, tracer sans l'indicateur
            logger.info(f"Tentative de tracé sans {indicator_name}...")
            self.plot_ohlcv(data, limit=limit)

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
        Trace un graphique OHLCV avec l'indicateur RSI.

        Args:
            data: DataFrame avec les données OHLCV
            rsi_serie: Série RSI pré-calculée (optionnelle)
            window: Période pour le calcul du RSI
            title: Titre du graphique
            limit: Nombre maximum de bougies à afficher
            price_column: Colonne de prix à utiliser pour le calcul
        """
        self._plot_with_indicator(
            data=data,
            indicator_name="RSI",
            indicator_serie=rsi_serie,
            window=window,
            title=title,
            limit=limit,
            price_column=price_column,
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
        self._plot_with_indicator(
            data=data,
            indicator_name="SMA",
            indicator_serie=sma_serie,
            window=window,
            title=title,
            limit=limit,
            price_column=price_column,
            indicator_color=sma_color,
            line_width=line_width,
        )

    def plot_ema(
        self,
        data: pd.DataFrame,
        ema_serie: Optional[pd.Series] = None,
        window: int = 20,
        title: str = "Prix avec EMA",
        limit: Optional[int] = None,
        price_column: str = "close",
        ema_color: str = "blue",
        line_width: float = 1.5,
    ) -> None:
        """
        Trace un graphique OHLCV avec une Exponential Moving Average (EMA).
        """
        self._plot_with_indicator(
            data=data,
            indicator_name="EMA",
            indicator_serie=ema_serie,
            window=window,
            title=title,
            limit=limit,
            price_column=price_column,
            indicator_color=ema_color,
            line_width=line_width,
        )

    def plot_macd(
        self,
        data: pd.DataFrame,
        macd_df: Optional[pd.DataFrame] = None,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        title: str = "Prix avec MACD",
        limit: Optional[int] = None,
        price_column: str = "close",
    ) -> None:
        """
        Trace un graphique OHLCV avec l'indicateur MACD.

        Args:
            data: DataFrame avec données OHLCV.
            macd_df: DataFrame MACD pré-calculé (optionnel).
                    Doit contenir les colonnes:
                    ['MACD', 'MACD_signal', 'MACD_hist']
            fast: Période EMA rapide.
            slow: Période EMA lente.
            signal: Période EMA signal.
            title: Titre du graphique.
            limit: Nombre max de bougies à afficher.
            price_column: Colonne prix pour le calcul.
        """
        logger.info(f"Tracé du graphique avec MACD ({fast}, {slow}, {signal})")

        if data.empty:
            raise ValueError("Données vides")

        original_data = data.copy()

        # 1Calcul du MACD si non fourni
        if macd_df is None:
            macd_df = self.calculator.calculate_macd(
                original_data,
                fast=fast,
                slow=slow,
                signal=signal,
                price_column=price_column,
                return_with_prices=False,
            )

        if not isinstance(macd_df, pd.DataFrame):
            raise ValueError("Le MACD doit être un DataFrame")

        required_cols = {"MACD", "MACD_signal", "MACD_hist"}
        if not required_cols.issubset(macd_df.columns):
            raise ValueError(
                "Le DataFrame MACD doit contenir : "
                "['MACD', 'MACD_signal', 'MACD_hist']"
            )

        # Alignement index
        macd_df = macd_df.loc[macd_df.index.intersection(original_data.index)]

        data = original_data.loc[macd_df.index]

        # Appliquer limite
        if limit and len(data) > limit:
            data = data.iloc[-limit:]
            macd_df = macd_df.iloc[-limit:]

        # Supprimer NaN
        valid_mask = macd_df["MACD"].notna()
        if not valid_mask.any():
            raise ValueError("Le MACD ne contient que des NaN")

        data = data[valid_mask]
        macd_df = macd_df[valid_mask]

        # Préparer données mplfinance
        plot_data = self._prepare_data_for_mplfinance(data)

        # Création des addplots MACD (panel secondaire)
        macd_line = mpf.make_addplot(
            macd_df["MACD"],
            panel=1,
            color="blue",
            width=1.5,
            ylabel="MACD",
        )

        signal_line = mpf.make_addplot(
            macd_df["MACD_signal"],
            panel=1,
            color="orange",
            width=1.2,
        )

        hist_colors = ["green" if v >= 0 else "red" for v in macd_df["MACD_hist"]]

        histogram = mpf.make_addplot(
            macd_df["MACD_hist"],
            type="bar",
            panel=1,
            color=hist_colors,
            alpha=0.6,
        )

        addplots = [macd_line, signal_line, histogram]

        # Configuration graphique
        plot_kwargs = self.default_plot_kwargs.copy()
        plot_kwargs.update(
            {
                "title": f"{title} ({fast},{slow},{signal})",
                "addplot": addplots,
                "volume": True,
                "panel_ratios": (3, 3, 1),
                "main_panel": 0,
                "volume_panel": 2,
            }
        )

        # Plot
        try:
            mpf.plot(plot_data, **plot_kwargs)
            logger.info(f"MACD tracé avec succès: {len(data)} bougies")
        except Exception as e:
            logger.error(f"Erreur lors du tracé MACD: {str(e)}")
            logger.info("Tentative de tracé sans MACD...")
            self.plot_ohlcv(data, limit=limit)

    def plot_bollinger_bands(
        self,
        data: pd.DataFrame,
        bb_df: Optional[pd.DataFrame] = None,
        window: int = 20,
        std: float = 2.0,
        title: str = "Prix avec Bandes de Bollinger",
        limit: Optional[int] = None,
        price_column: str = "close",
        middle_color: str = "orange",
        upper_color: str = "green",
        lower_color: str = "red",
    ) -> None:
        """
        Trace un graphique OHLCV avec les bandes de Bollinger.
        """
        logger.info(
            f"Tracé du graphique avec Bandes de Bollinger (window: {window}, std: {std})"
        )

        if data.empty:
            raise ValueError("Données vides")

        original_data = data.copy()

        # Calcul des bandes de Bollinger si non fournies
        if bb_df is None:
            bb_df = self.calculator.calculate_bollinger_bands(
                original_data,
                window=window,
                price_column=price_column,
                std=std,
            )

        if not isinstance(bb_df, pd.DataFrame):
            raise ValueError("Les bandes de Bollinger doivent être un DataFrame")

        required_cols = {"BB_middle", "BB_upper", "BB_lower"}
        if not required_cols.issubset(bb_df.columns):
            raise ValueError(
                "Le DataFrame des bandes de Bollinger doit contenir : "
                "['BB_middle', 'BB_upper', 'BB_lower']"
            )

        # Alignement des index
        bb_df = bb_df.loc[bb_df.index.intersection(original_data.index)]
        data = original_data.loc[bb_df.index]

        # Appliquer la limite
        if limit and len(data) > limit:
            data = data.iloc[-limit:]
            bb_df = bb_df.iloc[-limit:]

        # Supprimer les NaN
        valid_mask = bb_df["BB_middle"].notna()
        if not valid_mask.any():
            raise ValueError("Les bandes de Bollinger ne contiennent que des NaN")

        data = data[valid_mask]
        bb_df = bb_df[valid_mask]

        # Préparer les données pour mplfinance
        plot_data = self._prepare_data_for_mplfinance(data)

        # Création des addplots pour les bandes de Bollinger
        middle_band = mpf.make_addplot(
            bb_df["BB_middle"],
            color=middle_color,
            width=1.5,
            label=f"Bande centrale ({window})",
        )

        upper_band = mpf.make_addplot(
            bb_df["BB_upper"],
            color=upper_color,
            width=1.2,
            linestyle="--",
            label=f"Bande supérieure ({window}, {std}σ)",
        )

        lower_band = mpf.make_addplot(
            bb_df["BB_lower"],
            color=lower_color,
            width=1.2,
            linestyle="--",
            label=f"Bande inférieure ({window}, {std}σ)",
        )

        addplots = [middle_band, upper_band, lower_band]

        # Configuration du graphique
        plot_kwargs = self.default_plot_kwargs.copy()
        plot_kwargs.update(
            {
                "title": f"{title} (window: {window}, std: {std})",
                "addplot": addplots,
                "volume": True,
                "returnfig": True,  # Important pour récupérer la figure
            }
        )

        # Tracé avec mplfinance
        fig, axes = mpf.plot(plot_data, **plot_kwargs)

        # Ajout du remplissage avec matplotlib
        for ax in axes:
            if ax.get_label() == "main":
                ax.fill_between(
                    plot_data.index,
                    bb_df["BB_lower"],
                    bb_df["BB_upper"],
                    color="gray",
                    alpha=0.1,
                    label="Écart-type",
                )
                ax.legend()

        plt.show()
