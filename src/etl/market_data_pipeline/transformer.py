import pandas as pd
from datetime import datetime
from logger_settings import logger
from src.models.global_snapshot import GlobalMarketSnapshot
from src.models.global_market_cap import GlobalMarketCap
from src.models.global_market_volume import GlobalMarketVolume
from src.models.global_market_dominance import GlobalMarketDominance
from src.models.top_crypto_snapshot import TopCryptoSnapshot
from src.models.top_crypto import TopCrypto
from src.models.crypto_detail_snapshot import CryptoDetailSnapshot
from src.models.crypto_detail import CryptoDetail
import json


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

    def transform_crypto_details(self, raw_data: list):
        """
        Transforme les détails des cryptomonnaies en objets SQLAlchemy.

        Args:
            raw_data: Liste des détails depuis CoinGecko

        Returns:
            tuple: (snapshot, list[CryptoDetail])
        """
        try:
            logger.info(f"Transformation des détails de {len(raw_data)} cryptos")

            snapshot = CryptoDetailSnapshot(
                snapshot_time=datetime.utcnow(),
                cryptos_count=len(raw_data),
            )

            details = []
            for item in raw_data:
                links = item.get("links", {})
                community = item.get("community_data", {})
                developer = item.get("developer_data", {})
                market = item.get("market_data", {})
                image = item.get("image", {})

                detail = CryptoDetail(
                    snapshot_id=None,
                    crypto_id=item.get("id"),
                    symbol=item.get("symbol", "").upper(),
                    name=item.get("name"),
                    rank=item.get("market_cap_rank"),
                    categories=json.dumps(item.get("categories", []))
                    if item.get("categories")
                    else None,
                    genesis_date=item.get("genesis_date"),
                    hashing_algorithm=item.get("hashing_algorithm"),
                    block_time_minutes=item.get("block_time_in_minutes"),
                    image_large=image.get("large"),
                    image_small=image.get("small"),
                    links_homepage=json.dumps(links.get("homepage", []))
                    if links.get("homepage")
                    else None,
                    links_blockchain_site=json.dumps(links.get("blockchain_site", []))
                    if links.get("blockchain_site")
                    else None,
                    links_whitepaper=links.get("whitepaper"),
                    links_reddit=links.get("subreddit_url"),
                    links_twitter=links.get("twitter_screen_name"),
                    community_twitter=community.get("twitter_followers"),
                    community_reddit=community.get("reddit_subscribers"),
                    community_facebook=community.get("facebook_likes"),
                    developer_stars=developer.get("stars"),
                    developer_forks=developer.get("forks"),
                    developer_subscribers=developer.get("subscribers"),
                    developer_issues=developer.get("total_issues"),
                    developer_pull_requests=developer.get("total_pull_requests"),
                    market_cap_rank=market.get("market_cap_rank"),
                    market_cap=market.get("market_cap", {}).get("usd"),
                    total_volume=market.get("total_volume", {}).get("usd"),
                    high_24h=market.get("high_24h", {}).get("usd"),
                    low_24h=market.get("low_24h", {}).get("usd"),
                    price_change_24h=market.get("price_change_24h"),
                    price_change_pct_24h=market.get("price_change_percentage_24h"),
                    ath_price=market.get("ath", {}).get("usd"),
                    ath_date=market.get("ath_date", {}).get("usd"),
                    ath_change_pct=market.get("ath_change_percentage", {}).get("usd"),
                    atl_price=market.get("atl", {}).get("usd"),
                    atl_date=market.get("atl_date", {}).get("usd"),
                    atl_change_pct=market.get("atl_change_percentage", {}).get("usd"),
                    circulating_supply=market.get("circulating_supply"),
                    total_supply=market.get("total_supply"),
                    max_supply=market.get("max_supply"),
                    last_updated=datetime.utcnow(),
                )
                details.append(detail)

            logger.info(
                f"✅ Transformation crypto details réussie: snapshot + {len(details)} détails"
            )
            return snapshot, details

        except Exception as e:
            logger.error(f"❌ Échec transformation crypto details: {e}")
            raise TransformationErrorMarketData(e)
