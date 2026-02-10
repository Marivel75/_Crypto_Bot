"""
Module pour le calcul des indicateurs techniques.
Ce module contient des fonctions pour calculer divers indicateurs techniques
comme les moyennes mobiles, RSI, MACD, etc.
"""

import pandas as pd
from typing import List, Union, Optional
from logger_settings import logger


class TechnicalCalculator:
    """
    Classe pour le calcul des indicateurs techniques.
    """

    def __init__(self):
        pass

    def _prepare_data(
        self,
        data: Union[pd.DataFrame, List[float]],
        price_column: str = "close",
    ) -> pd.Series:
        """
        Prépare les données pour le calcul des indicateurs.
        Retourne une pd.Series des prix.
        """
        if isinstance(data, pd.DataFrame):
            if price_column not in data.columns:
                raise ValueError(
                    f"Le DataFrame doit contenir une colonne '{price_column}'"
                )
            return data[price_column]
        elif isinstance(data, list):
            return pd.Series(data)
        else:
            raise TypeError(
                "Type de données non supporté. Utilisez pandas.DataFrame ou list"
            )

    def _validate_window(
        self,
        window: int,
        data_length: int,
    ) -> None:
        """
        Valide que la fenêtre est compatible avec la longueur des données.
        """
        if window > data_length:
            raise ValueError(
                f"La fenêtre ({window}) ne peut pas être supérieure à la longueur des données ({data_length})"
            )

    def _handle_fillna(
        self,
        serie: pd.Series,
        fillna: Optional[Union[str, int, float]] = None,
    ) -> pd.Series:
        """
        Gère le remplissage des NaN selon la méthode spécifiée.
        """
        if fillna is not None:
            if isinstance(fillna, (int, float)):
                serie = serie.fillna(fillna)
            else:
                serie = serie.fillna(method=fillna)
        return serie

    def _return_result(
        self,
        serie: pd.Series,
        original_data: Union[pd.DataFrame, List[float]],
    ) -> Union[pd.Series, List[float]]:
        """
        Retourne le résultat sous le bon format (pd.Series ou list).
        """
        if isinstance(original_data, pd.DataFrame):
            return serie
        else:
            return serie.tolist()

    def calculate_sma(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 20,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
    ) -> Union[pd.Series, List[float]]:
        """
        Calcule et retourne la liste Simple Moving Average (SMA) pour une série de données.
        """
        try:
            close_prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(close_prices))
            sma = close_prices.rolling(window=window).mean()
            sma = self._handle_fillna(sma, fillna)
            return self._return_result(sma, data)
        except Exception as e:
            logger.error(f"Erreur dans le calcul de la SMA: {e}")
            raise

    def calculate_rsi(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 14,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
        max_values: Optional[int] = None,  # Nouvelle option pour limiter le calcul
    ) -> Union[pd.Series, List[float]]:
        """
        Calcule le Relative Strength Index (RSI) pour une série de données.
        """
        try:
            prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(prices))

            # Appliquer la limite si spécifiée
            if max_values is not None and len(prices) > max_values:
                logger.warning(
                    f"Limitation du calcul RSI à {max_values} valeurs (sur {len(prices)} disponibles)."
                )
                prices = prices.iloc[-max_values:]

            # Calcul des différences
            deltas = prices.diff()

            # Moyennes des gains et des pertes
            gains = deltas.clip(lower=0)
            losses = -deltas.clip(upper=0)

            avg_gain = gains.rolling(window=window, min_periods=window).mean()
            avg_loss = losses.rolling(window=window, min_periods=window).mean()

            # Calcul du RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Gestion des NaN
            rsi = self._handle_fillna(rsi, fillna)

            return self._return_result(rsi, data)

        except Exception as e:
            logger.error(f"Erreur dans le calcul du RSI: {e}")
            raise
