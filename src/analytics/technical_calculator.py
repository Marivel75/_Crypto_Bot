"""
Module pour le calcul des indicateurs techniques.
Utilise pandas_ta_classic
"""

import pandas as pd
from typing import List, Union, Optional
from logger_settings import logger

# Tentative d'import de pandas_ta_classic
try:
    import pandas_ta_classic as ta
except ImportError:
    raise ImportError(
        "La bibliothèque 'pandas_ta_classic' est requise. "
        "Installez-la avec : pip install pandas-ta-classic"
    )


class TechnicalCalculator:
    """
    Classe pour le calcul des indicateurs techniques.
    Tous les calculs sont délégués à pandas_ta_classic.
    """

    def __init__(self):
        pass

    # ----------------------------------------------------------------------
    # Méthodes privées de préparation / post-traitement
    # ----------------------------------------------------------------------
    def _prepare_data(
        self,
        data: Union[pd.DataFrame, List[float]],
        price_column: str = "close",
    ) -> pd.Series:
        """Prépare les données et retourne une pd.Series des prix."""
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
        """Vérifie que la fenêtre est compatible avec la longueur des données."""
        if window > data_length:
            raise ValueError(
                f"La fenêtre ({window}) ne peut pas être supérieure à la longueur des données ({data_length})"
            )

    def _handle_fillna(
        self,
        serie: pd.Series,
        fillna: Optional[Union[str, int, float]] = None,
    ) -> pd.Series:
        """Remplit les NaN selon la méthode ou valeur spécifiée."""
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
        """Retourne le résultat sous le même type que l'entrée."""
        if isinstance(original_data, pd.DataFrame):
            return serie
        else:
            return serie.tolist()

    def _return_multivariate_result(
        self,
        df: pd.DataFrame,
        original_data: Union[pd.DataFrame, List[float]],
        main_column: str = None,
    ) -> Union[pd.DataFrame, List[float]]:
        """
        Retourne un résultat multivarié sous le même type que l'entrée.
        - Si l'entrée est un DataFrame : retourne le DataFrame entier.
        - Si l'entrée est une liste : retourne une liste de la colonne principale spécifiée.
        """
        if isinstance(original_data, pd.DataFrame):
            return df
        else:
            if main_column is None:
                # Par défaut, prendre la première colonne
                main_column = df.columns[0]
            return df[main_column].tolist()

    # ----------------------------------------------------------------------
    # Calculs des indicateurs techniques
    # ----------------------------------------------------------------------
    def calculate_sma(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 20,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
    ) -> Union[pd.Series, List[float]]:
        """
        Calcule la Moyenne Mobile Simple (SMA – Simple Moving Average).

        La SMA est la moyenne arithmétique des prix de clôture sur une période donnée.
        Elle permet de lisser l'évolution du prix pour identifier plus facilement la tendance.
        Plus la période (`window`) est longue, plus la courbe est lisse et moins elle réagit aux mouvements récents.
        La SMA est un indicateur retardataire : elle suit le prix avec un décalage.

        Formule :
            SMA_t = (Prix_t + Prix_{t-1} + ... + Prix_{t-window+1}) / window

        Utilisations courantes :
            - Confirmation de tendance (prix au‑dessus de la SMA → tendance haussière).
            - Niveaux de support / résistance dynamiques.
            - Croisement de deux SMA (ex. SMA20 / SMA50) comme signaux d'achat/vente.
        """
        try:
            prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(prices))

            # pandas_ta.sma retourne une Series avec le même index
            sma = ta.sma(prices, length=window)

            # Gestion des NaN
            sma = self._handle_fillna(sma, fillna)

            return self._return_result(sma, data)

        except Exception as e:
            logger.error(f"Erreur dans le calcul de la SMA: {e}")
            raise

    def calculate_ema(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 20,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
    ) -> Union[pd.Series, List[float]]:
        """
        Calcule la Moyenne Mobile Exponentielle (EMA – Exponential Moving Average).

        L'EMA est une moyenne mobile qui accorde davantage de poids aux prix les plus récents.
        Elle réagit plus rapidement aux changements de prix que la SMA (Simple Moving Average),
        ce qui la rend plus adaptée pour capter le début d'une nouvelle tendance.

        Formule :
            EMA_t = Prix_t * coef + EMA_{t-1} * (1 - α)
            avec coef = 2 / (window + 1)  (facteur de lissage exponentiel)

        La première valeur de l'EMA est généralement initialisée avec la SMA de la période.

        Utilisations courantes :
            - Suivi de tendance : plus réactive que la SMA.
            - Base de calcul d'autres indicateurs (MACD, etc.).
            - Niveaux de support/résistance dynamiques souvent plus précis que la SMA.
            - Croisement de deux EMA (ex. EMA12 / EMA26) pour générer des signaux.
        """
        try:
            prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(prices))

            ema = ta.ema(prices, length=window)
            ema = self._handle_fillna(ema, fillna)

            return self._return_result(ema, data)

        except Exception as e:
            logger.error(f"Erreur dans le calcul de l'EMA: {e}")
            raise

    def calculate_rsi(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 14,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
        max_values: Optional[int] = None,
    ) -> Union[pd.Series, List[float]]:
        """
        Calcule le Relative Strength Index (RSI).

        Le RSI est un oscillateur de momentum qui mesure la vitesse et l'ampleur des variations de prix.
        Il oscille entre 0 et 100 et est principalement utilisé pour identifier des conditions de surachat
        (généralement au-dessus de 70) ou de survente (généralement en dessous de 30).

        Formule (méthode de Wilder) :
            RSI = 100 - (100 / (1 + RS))
            où RS = Moyenne des gains / Moyenne des pertes sur la période `window`.
            La première moyenne est simple (SMA), puis les suivantes sont lissées :
            Moyenne_gain_t = (Moyenne_gain_{t-1} * (window-1) + gain_t) / window
            Moyenne_perte_t = (Moyenne_perte_{t-1} * (window-1) + perte_t) / window

        Utilisations courantes :
            - Détection de surachat (> 70) ou survente (< 30) → retournement potentiel.
            - Divergences : le prix fait un nouveau plus haut mais le RSI fait un plus haut moins élevé
            (divergence baissière) ou l'inverse (divergence haussière).
            - Seuils personnalisables selon le contexte (ex. 80/20 en tendance forte).
        """
        try:
            prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(prices))

            # Application de la limitation éventuelle max_values: prend les N dernières valeurs, pour réduire la charge mémoire sur de très gros jeux de données.
            if max_values is not None and len(prices) > max_values:
                logger.warning(
                    f"Limitation du calcul RSI à {max_values} valeurs (sur {len(prices)} disponibles)."
                )
                prices = prices.iloc[-max_values:]

            rsi = ta.rsi(prices, length=window)
            rsi = self._handle_fillna(rsi, fillna)

            return self._return_result(rsi, data)

        except Exception as e:
            logger.error(f"Erreur dans le calcul du RSI: {e}")
            raise

    def calculate_macd(
        self,
        data: Union[pd.DataFrame, List[float]],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        price_column: str = "close",
        fillna: Optional[Union[str, int, float]] = None,
        return_with_prices: bool = False,
    ) -> Union[pd.DataFrame, List[float]]:
        """
        Calcule le MACD (Moving Average Convergence Divergence).

        ... (docstring existante, à compléter avec le nouveau paramètre) ...

        Args:
            ...
            return_with_prices (bool, optional):
                Si True et que `data` est un DataFrame, retourne une copie du DataFrame
                original avec les colonnes MACD ajoutées. Idéal pour un affichage direct.
                Si `data` est une liste, ce paramètre est ignoré.
                Par défaut, False (retourne uniquement les 3 colonnes MACD ou la liste MACD).

        Returns:
            Union[pd.DataFrame, List[float]]:
                - Si return_with_prices=False (défaut) : identique au comportement actuel.
                - Si return_with_prices=True et data est un DataFrame :
                    DataFrame original avec les colonnes 'MACD', 'MACD_signal', 'MACD_hist' ajoutées.
                - Si data est une liste : inchangé (liste de la ligne MACD).
        """
        try:
            prices = self._prepare_data(data, price_column)
            self._validate_window(slow, len(prices))

            # Calcul du MACD
            macd_df = ta.macd(prices, fast=fast, slow=slow, signal=signal)
            macd_df.columns = ["MACD", "MACD_signal", "MACD_hist"]

            # Gestion des NaN
            if fillna is not None:
                macd_df = macd_df.fillna(fillna)

            if return_with_prices and isinstance(data, pd.DataFrame):
                # Fusionner avec les données originales
                result = data.copy()
                for col in macd_df.columns:
                    result[col] = macd_df[col]
                return result
            else:
                # retourne seulement les données macd
                if isinstance(data, pd.DataFrame):
                    return macd_df
                else:
                    return macd_df["MACD"].tolist()

        except Exception as e:
            logger.error(f"Erreur dans le calcul du MACD: {e}")
            raise

    def calculate_bollinger_bands(
        self,
        data: Union[pd.DataFrame, List[float]],
        window: int = 20,
        price_column: str = "close",
        std: float = 2.0,
        fillna: Optional[Union[str, int, float]] = None,
    ) -> Union[pd.DataFrame, List[float]]:
        """
        Calcule les Bollinger Bands (BB).

        Les Bollinger Bands permettent d'identifier les périodes de faible ou forte volatilité et les niveaux de surachat/survente.
        Elles se composent de :
            - Middle Band (MB) : SMA sur `window` périodes
            - Upper Band (UB) : MB + (std * écart-type)
            - Lower Band (LB) : MB - (std * écart-type)

        Formules :
            MB_t = SMA_t
            UB_t = MB_t + std * STD_t
            LB_t = MB_t - std * STD_t

        Args:
            data: DataFrame OHLCV ou liste de prix.
            window: Période de calcul de la SMA (default 20)
            price_column: Colonne contenant les prix (default "close")
            std: Nombre d'écarts-types pour UB/LB (default 2.0)
            fillna: Valeur ou méthode pour remplacer les NaN (optionnel)

        Returns:
            DataFrame avec colonnes :
                'BB_middle', 'BB_upper', 'BB_lower'
            ou liste de la colonne 'BB_middle' si input liste.
        """
        try:
            prices = self._prepare_data(data, price_column)
            self._validate_window(window, len(prices))

            bb_df = ta.bbands(prices, length=window, std=std)
            # pandas_ta_classic retourne des colonnes nommées : ['BBL_20_2.0','BBM_20_2.0','BBU_20_2.0','BBB_20_2.0','BBP_20_2.0']
            # On renomme pour la clarté
            bb_df = bb_df.rename(
                columns={
                    bb_df.columns[1]: "BB_middle",  # SMA
                    bb_df.columns[0]: "BB_lower",  # Lower Band
                    bb_df.columns[2]: "BB_upper",  # Upper Band
                }
            )[["BB_middle", "BB_upper", "BB_lower"]]

            # Gestion des NaN
            bb_df = self._handle_fillna(bb_df, fillna)

            return self._return_multivariate_result(
                bb_df, data, main_column="BB_middle"
            )

        except Exception as e:
            logger.error(f"Erreur dans le calcul des Bollinger Bands: {e}")
            raise
