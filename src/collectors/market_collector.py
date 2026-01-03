import pandas as pd
from src.services.binance_client import BinanceClient
from src.services.db import get_engine
from sqlalchemy.exc import IntegrityError


class MarketCollector:
    def __init__(self, pairs, timeframes):
        self.pairs = pairs
        self.timeframes = timeframes
        self.client = BinanceClient()
        self.engine = get_engine()

    def fetch_and_store(self):
        for pair in self.pairs:
            for tf in self.timeframes:
                # Récupère les bougies
                ohlcv = self.client.fetch_ohlcv(pair, tf)

                # Convertit en DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )
                df["symbol"] = pair
                df["timeframe"] = tf

                # Convert timestamp en datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

                try:
                    df.to_sql("ohlcv", self.engine, if_exists="append", index=False)
                    print(f"✅ {pair} {tf} sauvegardé")
                except IntegrityError:
                    print(f"⚠️ Doublons détectés pour {pair} {tf}, ignorés")
