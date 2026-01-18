"""
Module de gestion des clients d'exchange avec context managers. Fournit des
classes pour gérer les connexions aux exchanges.
"""

from contextlib import contextmanager
from typing import Any, Generator

from src.config.logger_settings import logger
from src.services.exchange_factory import ExchangeFactory


class ExchangeClient:
    """
    Context manager pour la gestion des clients d'exchange, garantit que les
    clients d'exchange sont correctement initialisés et fermés, même en cas
    d'erreur.
    """

    def __init__(self, exchange_name: str) -> None:
        self.exchange_name = exchange_name
        self.client: Any = None

    def __enter__(self) -> Any:
        """
        Initialise et retourne le client d'exchange ccxt.Exchange.
        """
        try:
            self.client = ExchangeFactory.create_exchange(self.exchange_name)
            logger.debug(f"✅ Client {self.exchange_name} initialisé")
            return self.client
        except Exception as e:
            logger.error(f"❌ Échec de l'initialisation du client {self.exchange_name}: {e}")
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> bool:
        """
        Fermeture propre du client, même en cas d'erreur.
        Arguments:
            exc_type: Type de l'exception si une erreur s'est produite
            exc_val: Valeur de l'exception
            exc_tb: Traceback de l'exception
        """
        try:
            if self.client:
                # Fermer proprement le client si la méthode existe
                if hasattr(self.client, "close"):
                    self.client.close()
                logger.debug(f"✅ Client {self.exchange_name} fermé")
        except Exception as e:
            logger.error(f"❌ Échec de la fermeture du client {self.exchange_name}: {e}")
            if exc_type is not None:
                return False
        return True


@contextmanager
def exchange_client(exchange_name: str) -> Generator[Any, None, None]:
    """
    Context manager pour les clients d'exchange (version fonctionnelle).
    Arguments:
        exchange_name: Nom de l'exchange (binance, kraken, coinbase)
    Yields:
        ccxt.Exchange: Client d'exchange initialisé
    """
    client = None
    try:
        client = ExchangeFactory.create_exchange(exchange_name)
        logger.debug(f"✅ Client {exchange_name} initialisé")
        yield client
    except Exception as e:
        logger.error(f"❌ Échec du client {exchange_name}: {e}")
        raise
    finally:
        if client and hasattr(client, "close"):
            try:
                client.close()
                logger.debug(f"✅ Client {exchange_name} fermé")
            except Exception as e:
                logger.error(f"❌ Échec fermeture client {exchange_name}: {e}")
