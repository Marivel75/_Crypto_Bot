"""
Module pour le calcul des indicateurs techniques.
Ce module contient des fonctions pour calculer divers indicateurs techniques
comme les moyennes mobiles, RSI, MACD, etc.
"""

import pandas as pd
from typing import List, Union, Optional
from logger_settings import logger


def calculate_sma(
    data: Union[pd.DataFrame, List[float]],
    window: int = 20,
    price_column: str = "close",
    fillna: Optional[Union[str, int, float]] = None,
) -> Union[pd.Series, List[float]]:
    """
    Calcule la Simple Moving Average (SMA) pour une série de données.

    Args:
        data: DataFrame pandas avec une colonne de prix ou une liste de valeurs de prix.
        window: Période pour le calcul de la SMA (par défaut 20).
        price_column: Nom de la colonne de prix (si DataFrame). Par défaut 'close'.
        fillna: Méthode ou valeur pour remplir les NaN. Options :
            - None (par défaut) : Conserve les NaN (recommandé pour les analyses).
            - Valeur numérique (ex: 0) : Remplace les NaN par cette valeur.
            - 'ffill' : Remplace les NaN par la dernière valeur valide (Forward Fill).
              Cas d'usage : Visualisation de graphiques sans trous, ou pour des séries temporelles où on suppose que la valeur reste stable en l'absence de données.
              Exemple : Remplir les SMA manquantes dans un historique de prix pour afficher une courbe continue.
            - 'bfill' : Remplace les NaN par la première valeur valide suivante (Backward Fill).
              Cas d'usage : Moins courant, mais utile pour combler des trous avec des données futures connues (ex: données retardées).
              Exemple : Remplir les SMA manquantes en début de série si on connaît les valeurs futures.

    Returns:
        Série pandas ou liste contenant les valeurs SMA.

    Exemples:
        >>> data = pd.DataFrame({'close': [1, 2, 3, 4, 5]})
        >>> calculate_sma(data, window=3)
        0     NaN  # Pas assez de données pour calculer la SMA
        1     NaN
        2     2.0  # (1+2+3)/3
        3     3.0  # (2+3+4)/3
        4     4.0  # (3+4+5)/3
        Name: close, dtype: float64

        >>> calculate_sma(data, window=3, fillna='ffill')
        0     NaN  # Aucune valeur précédente pour remplir
        1     NaN
        2     2.0
        3     3.0
        4     4.0
        Name: close, dtype: float64

        >>> calculate_sma(data, window=3, fillna=0)
        0     0.0  # NaN remplacés par 0
        1     0.0
        2     2.0
        3     3.0
        4     4.0
        Name: close, dtype: float64
    """
    try:
        if isinstance(data, pd.DataFrame):
            if price_column not in data.columns:
                raise ValueError(
                    f"Le DataFrame doit contenir une colonne '{price_column}'"
                )
            close_prices = data[price_column]
        elif isinstance(data, list):
            close_prices = pd.Series(data)
        else:
            raise TypeError(
                "Type de données non supporté. Utilisez pandas.DataFrame ou list"
            )

        if window > len(close_prices):
            raise ValueError(
                f"La fenêtre ({window}) ne peut pas être supérieure à la longueur des données ({len(close_prices)})"
            )

        sma = close_prices.rolling(window=window).mean()

        if fillna is not None:
            if isinstance(fillna, (int, float)):
                sma = sma.fillna(fillna)
            else:
                sma = sma.fillna(method=fillna)

        if isinstance(data, pd.DataFrame):
            return sma
        else:
            return sma.tolist()

    except Exception as e:
        logger.error(f"Erreur dans le calcul de la SMA: {e}")
        raise
