import pandas as pd
from datetime import datetime
from logger_settings import logger
from src.models.global_snapshot import GlobalMarketSnapshot
from src.models.global_market_cap import GlobalMarketCap
from src.models.global_market_volume import GlobalMarketVolume
from src.models.global_market_dominance import GlobalMarketDominance
from src.models.top_crypto_snapshot import TopCryptoSnapshot
from src.models.top_crypto import TopCrypto


class TransformationErrorMarketData(Exception):
    """Exception levée lors d'une erreur de transformation MarketData."""

    pass


class MarketDataTransformer:
    """
    Transforme les données brutes CoinGecko en objets SQLAlchemy prêts à être chargés.
    """

    def transform(self, raw_data: dict):
        """
        raw_data : dict renvoyé par CoinGecko pour global_market
        Retourne :
            snapshot: GlobalMarketSnapshot
            caps: list[GlobalMarketCap]
            volumes: list[GlobalMarketVolume]
            dominance: list[GlobalMarketDominance]
        """
        try:
            logger.info("Transformation des données global_market")

            # Snapshot principal
            snapshot = GlobalMarketSnapshot(
                timestamp=datetime.utcfromtimestamp(raw_data["updated_at"]),
                active_cryptocurrencies=raw_data.get("active_cryptocurrencies"),
                upcoming_icos=raw_data.get("upcoming_icos"),
                ongoing_icos=raw_data.get("ongoing_icos"),
                ended_icos=raw_data.get("ended_icos"),
                markets=raw_data.get("markets"),
                market_cap_change_24h=raw_data.get(
                    "market_cap_change_percentage_24h_usd"
                ),
                volume_change_24h=raw_data.get("volume_change_percentage_24h_usd"),
            )

            # Market caps par devise
            caps = [
                GlobalMarketCap(
                    snapshot_id=None,  # sera fixé après insert snapshot
                    currency=cur,
                    value=val,
                )
                for cur, val in raw_data.get("total_market_cap", {}).items()
            ]

            # Volumes par devise
            volumes = [
                GlobalMarketVolume(snapshot_id=None, currency=cur, value=val)
                for cur, val in raw_data.get("total_volume", {}).items()
            ]

            # Dominance par devise
            dominance = [
                GlobalMarketDominance(snapshot_id=None, asset=asset, percentage=pct)
                for asset, pct in raw_data.get("market_cap_percentage", {}).items()
            ]

            logger.info(
                f"✅ Transformation réussie: snapshot + {len(caps)} caps, {len(volumes)} volumes, {len(dominance)} dominances"
            )
            return snapshot, caps, volumes, dominance

        except Exception as e:
            logger.error(f"❌ Échec transformation: {e}")
            raise TransformationErrorMarketData(e)

    def transform_top_cryptos(self, raw_data: list, vs_currency: str = "usd"):
        """
        Transforme les données des top cryptomonnaies en objets SQLAlchemy.

        Args:
            raw_data: Liste des cryptomonnaies depuis CoinGecko
            vs_currency: Devise de référence

        Returns:
            tuple: (snapshot, list[TopCrypto])
        """
        try:
            logger.info(f"Transformation des données top {len(raw_data)} cryptos")

            # Snapshot principal
            snapshot = TopCryptoSnapshot(
                snapshot_time=datetime.utcnow(),
                vs_currency=vs_currency,
            )

            # Liste des cryptos
            cryptos = []
            for item in raw_data:
                crypto = TopCrypto(
                    snapshot_id=None,
                    rank=item.get("market_cap_rank"),
                    crypto_id=item.get("id"),
                    symbol=item.get("symbol", "").upper(),
                    name=item.get("name"),
                    market_cap=item.get("market_cap"),
                    price=item.get("current_price"),
                    volume_24h=item.get("total_volume"),
                    price_change_pct_24h=item.get("price_change_percentage_24h"),
                )
                cryptos.append(crypto)

            logger.info(
                f"✅ Transformation top cryptos réussie: snapshot + {len(cryptos)} cryptos"
            )
            return snapshot, cryptos

        except Exception as e:
            logger.error(f"❌ Échec transformation top cryptos: {e}")
            raise TransformationErrorMarketData(e)
