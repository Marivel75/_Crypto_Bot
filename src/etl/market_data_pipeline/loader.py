from logger_settings import logger
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.models.global_snapshot import GlobalMarketSnapshot
from src.models.global_market_cap import GlobalMarketCap
from src.models.global_market_volume import GlobalMarketVolume
from src.models.global_market_dominance import GlobalMarketDominance
from src.models.top_crypto_snapshot import TopCryptoSnapshot
from src.models.top_crypto import TopCrypto


class LoadingErrorMarketData(Exception):
    """Exception levée lors d'un échec de chargement MarketData."""

    pass


class MarketDataLoader:
    """
    Charge les données global_market transformées dans la base via SQLAlchemy ORM.
    """

    def __init__(self, engine):
        self.engine = engine
        logger.info("MarketDataLoader initialisé avec SQLAlchemy Engine")

    def load(self, snapshot, caps, volumes, dominance):
        """
        snapshot : GlobalMarketSnapshot
        caps : list[GlobalMarketCap]
        volumes : list[GlobalMarketVolume]
        dominance : list[GlobalMarketDominance]
        """
        session = Session(self.engine)
        try:
            # Ajouter le snapshot principal
            session.add(snapshot)
            session.commit()  # commit pour récupérer snapshot.id
            logger.info(f"Snapshot inséré avec id={snapshot.id}")

            # Associer snapshot_id aux tables filles
            for item in caps + volumes + dominance:
                item.snapshot_id = snapshot.id

            # Bulk insert des tables filles
            session.bulk_save_objects(caps)
            session.bulk_save_objects(volumes)
            session.bulk_save_objects(dominance)
            session.commit()

            logger.info(
                f"✅ Chargement réussi: {len(caps)} caps, {len(volumes)} volumes, {len(dominance)} dominances"
            )
            return snapshot.id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"❌ Échec du chargement MarketData: {e}")
            raise LoadingErrorMarketData(e)
        finally:
            session.close()

    def load_top_cryptos(self, snapshot, cryptos):
        """
        Charge les données des top cryptomonnaies dans la base.

        Args:
            snapshot: TopCryptoSnapshot
            cryptos: list[TopCrypto]

        Returns:
            int: ID du snapshot créé
        """
        session = Session(self.engine)
        try:
            session.add(snapshot)
            session.commit()
            logger.info(f"Snapshot top cryptos inséré avec id={snapshot.id}")

            for crypto in cryptos:
                crypto.snapshot_id = snapshot.id

            session.bulk_save_objects(cryptos)
            session.commit()

            logger.info(f"✅ Chargement top cryptos réussi: {len(cryptos)} cryptos")
            return snapshot.id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"❌ Échec du chargement top cryptos: {e}")
            raise LoadingErrorMarketData(e)
        finally:
            session.close()
