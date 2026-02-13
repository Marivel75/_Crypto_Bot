import pandas as pd
from typing import Dict, List, Tuple, Optional
from logger_settings import logger


class TechnicalSignals:
    """
    Classe pour générer des signaux de trading à partir d'indicateurs techniques.
    Les indicateurs sont déjà calculés dans technical_calculators et présents dans un DataFrame.
    """

    @staticmethod
    def macd_cross(
        df: pd.DataFrame,
        macd_col: str = "MACD",
        signal_col: str = "MACD_signal",
        confirm_next_candle: bool = True,
    ) -> pd.DataFrame:
        """
        Ajoute les colonnes de signaux de croisement MACD.

        Args:
            confirm_next_candle: si True, décale le signal d'une bougie
                                pour éviter le lookahead bias.
        """
        df = df.copy()

        cross_up = (df[macd_col] > df[signal_col]) & (
            df[macd_col].shift(1) <= df[signal_col].shift(1)
        )

        cross_down = (df[macd_col] < df[signal_col]) & (
            df[macd_col].shift(1) >= df[signal_col].shift(1)
        )

        if confirm_next_candle:
            cross_up = cross_up.shift(1)
            cross_down = cross_down.shift(1)

        df["MACD_cross_up"] = cross_up.fillna(False)
        df["MACD_cross_down"] = cross_down.fillna(False)

        return df

    @staticmethod
    def get_macd_signals(
        df: pd.DataFrame,
        macd_col: str = "MACD",
        signal_col: str = "MACD_signal",
    ) -> Dict[str, List]:
        """
        Retourne un dictionnaire avec les dates/indices des signaux MACD.
        """
        df_signals = TechnicalSignals.macd_cross(df, macd_col, signal_col)
        return {
            "buy": df_signals[df_signals["MACD_cross_up"]].index.tolist(),
            "sell": df_signals[df_signals["MACD_cross_down"]].index.tolist(),
        }

    @staticmethod
    def rsi_conditions(
        df: pd.DataFrame,
        rsi_col: str = "RSI_14",
        overbought: float = 70,
        oversold: float = 30,
    ) -> pd.DataFrame:
        """
        Ajoute les colonnes de surachat / survente RSI.
        """
        df = df.copy()
        df["RSI_overbought"] = df[rsi_col] > overbought
        df["RSI_oversold"] = df[rsi_col] < oversold
        return df
