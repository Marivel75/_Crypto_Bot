"""
Construction des features ML à partir de données OHLCV.

Catégories de features produites :
  - Returns & momentum    : log-return, returns sur N périodes
  - Volatilité            : écart-type glissant des log-returns
  - Indicateurs techniques: RSI, MACD, Bollinger Bands, SMA, EMA
  - Structure des bougies : spread H/L, corps, mèches
  - Volume                : volume relatif, variation
  - Temporelles           : heure, jour, semaine, mois, week-end

Contrainte principale : aucune donnée future ne doit être utilisée.
Toutes les features sont calculées sur des données disponibles à l'instant t.
"""

import numpy as np
import pandas as pd

from logger_settings import logger
from src.analytics.technical_calculator import TechnicalCalculator

# Nombre minimum de lignes pour calculer les indicateurs avec window=50
_MIN_ROWS = 60


class FeatureBuilder:
    """
    Construit l'ensemble des features ML à partir d'un DataFrame OHLCV.

    Le DataFrame d'entrée doit correspondre à un seul (symbol, timeframe, exchange)
    et être trié par timestamp croissant.

    Usage::

        builder = FeatureBuilder()
        df_features = builder.build(df_ohlcv)
    """

    def __init__(self):
        self._calc = TechnicalCalculator()

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ajoute toutes les features au DataFrame OHLCV.

        Args:
            df: DataFrame avec au minimum les colonnes
                ``timestamp``, ``open``, ``high``, ``low``, ``close``, ``volume``.
                Doit être trié par timestamp croissant.

        Returns:
            Copie du DataFrame enrichie avec les features.
            Les premières lignes contiennent des NaN (warm-up des indicateurs) ;
            utilisez ``DatasetBuilder`` pour les supprimer proprement.
        """
        self._validate(df)

        result = df.copy().sort_values("timestamp").reset_index(drop=True)

        result = self._add_return_features(result)
        result = self._add_volatility_features(result)
        result = self._add_technical_features(result)
        result = self._add_candle_structure_features(result)
        result = self._add_volume_features(result)
        result = self._add_temporal_features(result)

        n_added = len(result.columns) - len(df.columns)
        logger.info(
            f"FeatureBuilder.build : {len(result)} lignes, "
            f"{len(result.columns)} colonnes totales (+{n_added} features ajoutées)."
        )
        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, df: pd.DataFrame) -> None:
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes OHLCV manquantes : {missing}")
        if len(df) < _MIN_ROWS:
            raise ValueError(
                f"Données insuffisantes : {len(df)} lignes (minimum requis : {_MIN_ROWS})."
            )

    # ------------------------------------------------------------------
    # Groupes de features
    # ------------------------------------------------------------------

    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Log-return à 1 période et returns simples sur 4, 12 et 24 périodes.

        Utilisation des returns (%) plutôt que des prix absolus pour garantir
        la stationnarité de la série — essentiel pour le ML sur séries temporelles.
        """
        close = df["close"]

        df["log_return_1"] = np.log(close / close.shift(1))

        for n in [4, 12, 24]:
            df[f"return_{n}"] = (close - close.shift(n)) / close.shift(n)

        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Volatilité réalisée = écart-type glissant des log-returns sur 5, 10 et 20 périodes.

        Capture les régimes de marché (calme vs turbulent) qui conditionnent
        fortement le comportement des prix.
        """
        log_ret = df["log_return_1"]

        for window in [5, 10, 20]:
            df[f"volatility_{window}"] = log_ret.rolling(window).std()

        return df

    def _add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Indicateurs techniques classiques.

        RSI       → momentum oscillateur (surachat / survente)
        MACD      → divergence de moyennes mobiles (direction + force)
        Bollinger → position relative du prix dans la bande (volatilité)
        SMA ratio → prix normalisé par rapport à sa moyenne (tendance)
        EMA ratio → idem, avec plus de réactivité aux prix récents
        """
        # RSI(14)
        df["rsi_14"] = self._calc.calculate_rsi(df, window=14)

        # MACD (12, 26, 9)
        macd_df = self._calc.calculate_macd(df)
        df["macd"] = macd_df["MACD"]
        df["macd_signal"] = macd_df["MACD_signal"]
        df["macd_hist"] = macd_df["MACD_hist"]

        # Bollinger Bands(20) → position normalisée + largeur relative
        bb_df = self._calc.calculate_bollinger_bands(df, window=20)
        bb_range = (bb_df["BB_upper"] - bb_df["BB_lower"]).replace(0, np.nan)
        bb_mid = bb_df["BB_middle"].replace(0, np.nan)

        df["bb_position"] = (df["close"] - bb_df["BB_lower"]) / bb_range
        df["bb_width"] = bb_range / bb_mid

        # SMA ratios : prix / SMA(n)  → 1 si le prix est sur sa moyenne
        for w in [7, 20, 50]:
            sma = self._calc.calculate_sma(df, window=w).replace(0, np.nan)
            df[f"sma_{w}_ratio"] = df["close"] / sma

        # EMA ratios
        for w in [9, 21]:
            ema = self._calc.calculate_ema(df, window=w).replace(0, np.nan)
            df[f"ema_{w}_ratio"] = df["close"] / ema

        return df

    def _add_candle_structure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Morphologie des bougies.

        hl_spread       → amplitude relative de la bougie (volatilité intra-période)
        body_ratio      → part du corps dans l'amplitude totale (0 = doji, 1 = marubozu)
        upper_wick_ratio→ mèche haute relative (rejet de la hausse)
        lower_wick_ratio→ mèche basse relative (rejet de la baisse)
        """
        hl = (df["high"] - df["low"]).replace(0, np.nan)
        body = abs(df["close"] - df["open"])
        close = df["close"].replace(0, np.nan)

        top = df[["open", "close"]].max(axis=1)
        bottom = df[["open", "close"]].min(axis=1)

        df["hl_spread"] = hl / close
        df["body_ratio"] = body / hl
        df["upper_wick_ratio"] = (df["high"] - top) / hl
        df["lower_wick_ratio"] = (bottom - df["low"]) / hl

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Features de volume.

        volume_ma_ratio → volume actuel / volume moyen sur 20 périodes
                          (> 1 = volume anormalement élevé → signal de confirmation)
        volume_change   → variation relative du volume par rapport à la période précédente
        """
        vol = df["volume"]
        vol_ma20 = vol.rolling(20).mean().replace(0, np.nan)

        df["volume_ma_ratio"] = vol / vol_ma20
        df["volume_change"] = (vol - vol.shift(1)) / vol.shift(1).replace(0, np.nan)

        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Features calendaires extraites du timestamp.

        Capturent les patterns saisonniers du marché crypto :
        - Intraday (heure) : volumes et volatilité plus élevés à l'ouverture des marchés US/EU
        - Hebdomadaire (jour) : week-ends généralement moins liquides
        - Mensuel : comportements liés aux expiries de futures
        """
        ts = pd.to_datetime(df["timestamp"])

        df["hour"] = ts.dt.hour
        df["day_of_week"] = ts.dt.dayofweek   # 0 = lundi, 6 = dimanche
        df["day_of_month"] = ts.dt.day
        df["month"] = ts.dt.month
        df["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)

        return df
