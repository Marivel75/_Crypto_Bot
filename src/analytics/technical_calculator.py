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

    def calculate_ema(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 20,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
    ) -> Union[pd.Series, List[float]]:
        """
        Calcule l'Exponential Moving Average (EMA) pour une série de prix : moyenne mobile pondérée qui donne plus de poids aux prix récents,
        ce qui la rend plus réactive aux nouvelles informations versus la SMA (Simple Moving Average).
        Utilisée pour identifier la tendance du marché.

        Args:
            data (Union[pd.DataFrame, List[float]]):
                Données d'entrée contenant les prix. Peut être un DataFrame pandas (avec une colonne spécifiée)
                ou une liste de valeurs numériques.
            window (int, optionnel):
                Période de lissage pour le calcul de l'EMA. Par défaut, 20.
                Plus la fenêtre est petite, plus l'EMA réagit rapidement aux changements de prix.
            price_column (str, optionnel):
                Nom de la colonne contenant les prix dans le DataFrame. Par défaut, "close".
                Ignoré si `data` est une liste.
            fillna (Union[str, int, float], optionnel):
                Méthode ou valeur pour remplir les NaN dans le résultat.
                Peut être une chaîne ("ffill", "bfill"), un entier ou un flottant.
                Par défaut, None (les NaN ne sont pas remplis).

        Returns:
            Union[pd.Series, List[float]]:
                Série pandas ou liste contenant les valeurs de l'EMA.
                Le type de retour dépend du type de `data` :
                - Si `data` est un DataFrame, retourne une pd.Series.
                - Si `data` est une liste, retourne une liste.

        Raises:
            ValueError:
                Si `window` est supérieur à la longueur des données ou si `price_column` n'existe pas dans le DataFrame.
            TypeError:
                Si `data` n'est ni un DataFrame ni une liste.

        Exemple:
            >>> calculator = TechnicalCalculator()
            >>> data = [10, 12, 15, 14, 18, 20, 22]
            >>> ema = calculator.calculate_ema(data, window=3)
            >>> print(ema)
            [nan, nan, 12.333..., 13.888..., 15.777..., 17.851..., 19.900...]
        """
        try:
            close_prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(close_prices))
            ema = close_prices.ewm(span=window, adjust=False).mean()
            ema = self._handle_fillna(ema, fillna)
            return self._return_result(ema, data)
        except Exception as e:
            logger.error(f"Erreur dans le calcul de l'EMA: {e}")
            raise
