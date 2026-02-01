"""
Module pour le calcul des indicateurs techniques.
Ce module contient des fonctions pour calculer divers indicateurs techniques
comme les moyennes mobiles, RSI, MACD, etc.
"""

import pandas as pd
import numpy as np
from typing import Union, Optional, List
from logger_settings import logger
from src.config.settings import ENVIRONMENT


def calculate_sma(
    data: Union[pd.DataFrame, pd.Series, List[float]],
    window: int = 20,
    price_column: str = "close",
    fillna: Optional[Union[str, int, float]] = None,
) -> Union[pd.Series, List[float]]:
    """
    Calcule la Simple Moving Average (SMA) pour une série de données.

    Args:
        data: DataFrame pandas avec une colonne de prix, une Series pandas ou une liste de valeurs de prix.
        window: Période pour le calcul de la SMA (par défaut 20).
        price_column: Nom de la colonne de prix (si DataFrame). Par défaut 'close'.
        fillna: Méthode ou valeur pour remplir les NaN. Options :
            - None (par défaut) : Conserve les NaN (recommandé pour les analyses).
            - Valeur numérique (ex: 0) : Remplace les NaN par cette valeur.
            - 'ffill' : Remplace les NaN par la dernière valeur valide (Forward Fill).
            - 'bfill' : Remplace les NaN par la première valeur valide suivante (Backward Fill).

    Returns:
        Série pandas ou liste contenant les valeurs SMA.

    Exemples:
        >>> data = pd.DataFrame({'close': [1, 2, 3, 4, 5]})
        >>> calculate_sma(data, window=3)
        0     NaN
        1     NaN
        2     2.0
        3     3.0
        4     4.0
        Name: close, dtype: float64
    """
    logger.debug(f"Calcul de la SMA (window={window}) (Environnement: {ENVIRONMENT})")

    try:
        # Convertir les données en Series pandas
        if isinstance(data, pd.DataFrame):
            if price_column not in data.columns:
                raise ValueError(
                    f"Le DataFrame doit contenir une colonne '{price_column}'"
                )
            close_prices = data[price_column]
        elif isinstance(data, pd.Series):
            close_prices = data
        elif isinstance(data, list):
            close_prices = pd.Series(data)
        else:
            raise TypeError(
                "Type de données non supporté. Utilisez pandas.DataFrame, pandas.Series ou list"
            )

        # Validation de la fenêtre
        if window <= 0:
            raise ValueError("La fenêtre doit être un entier positif")
        if window > len(close_prices):
            logger.warning(
                f"La fenêtre ({window}) est supérieure à la longueur des données ({len(close_prices)})"
            )

        # Calcul de la SMA
        sma = close_prices.rolling(window=window, min_periods=1).mean()

        # Gestion des NaN
        if fillna is not None:
            if isinstance(fillna, (int, float)):
                sma = sma.fillna(fillna)
            else:
                sma = sma.fillna(method=fillna)

        logger.debug(f"SMA calculée avec succès (Environnement: {ENVIRONMENT})")

        # Retourner le bon type selon l'entrée
        if isinstance(data, (pd.DataFrame, pd.Series)):
            return sma
        else:
            return sma.tolist()

    except Exception as e:
        logger.error(
            f"Erreur dans le calcul de la SMA (Environnement: {ENVIRONMENT}): {e}"
        )
        raise


class TechnicalIndicators:
    """
    Classe pour calculer et gérer les indicateurs techniques.
    Permet d'ajouter facilement de nouveaux indicateurs.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialise avec un DataFrame contenant les données de prix.
        """
        self.data = data.copy()
        logger.debug(f"TechnicalIndicators initialisé (Environnement: {ENVIRONMENT})")

    def add_sma(
        self,
        window: int = 20,
        price_column: str = "close",
        fillna: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Ajoute une colonne SMA au DataFrame.

        Args:
            window: Période pour le calcul de la SMA (par défaut 20).
            price_column: Nom de la colonne de prix (par défaut 'close').
            fillna: Méthode pour remplir les NaN.

        Returns:
            DataFrame avec la colonne SMA ajoutée.
        """
        sma = calculate_sma(self.data, window, price_column, fillna)
        self.data[f"sma_{window}"] = sma
        logger.debug(
            f"SMA-{window} ajoutée au DataFrame (Environnement: {ENVIRONMENT})"
        )
        return self.data

    def get_data(self) -> pd.DataFrame:
        """
        Retourne le DataFrame avec tous les indicateurs calculés.
        """
        return self.data

    # Méthodes pour d'autres indicateurs (à implémenter plus tard)
    # def add_rsi(self, window: int = 14) -> pd.DataFrame:
    #     pass

    # def add_macd(self) -> pd.DataFrame:
    #     pass
