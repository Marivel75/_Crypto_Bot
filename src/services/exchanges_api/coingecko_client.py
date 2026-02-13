import requests
from logger_settings import logger
from typing import Optional, Dict, List
from functools import wraps
import time


class CoinGeckoClient:
    """
    Client pour interagir avec l'API CoinGecko.
    Récupère les données globales de marché (market cap, volume, prix, etc.).
    """

    def __init__(self, base_url: Optional[str] = None, rate_limit_delay: float = 0.3):
        """
        Args:
            base_url: URL de base de l'API CoinGecko (optionnel, par défaut: "https://api.coingecko.com/api/v3").
            rate_limit_delay: Délai (en secondes) entre les requêtes pour respecter les limites de taux (default: 0.0).
        """
        self.base_url = base_url or "https://api.coingecko.com/api/v3"
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0

    def _rate_limit(self):
        """Gère le délai entre les requêtes pour respecter les limites de taux."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
            self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Effectue une requête à l'API CoinGecko.

        Args:
            endpoint: Point de terminaison de l'API (ex. "/coins/markets").
            params: Paramètres de la requête.

        Returns:
            Dict: Réponse JSON de l'API.

        Raises:
            requests.exceptions.RequestException: En cas d'erreur de requête.
        """
        self._rate_limit()
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête à {url}: {e}")
            raise

    def fetch_top_cryptos_by_market_cap(
        self,
        limit: int = 50,
        vs_currency: str = "usd",
        order: str = "market_cap_desc",
        sparkline: bool = False,
        price_change_percentage: str = "24h",
    ) -> List[Dict]:
        """
        Récupère les cryptomonnaies triées par capitalisation boursière.

        Args:
            limit: Nombre de cryptos à retourner (default 50).
            vs_currency: Devise de référence (ex. "usd", "eur").
            order: Tri des résultats (ex. "market_cap_desc", "volume_desc").
            sparkline: Inclure les graphiques sparkline (default False).
            price_change_percentage: Période pour le changement de prix (ex. "24h", "7d").

        Returns:
            List[Dict]: Liste des cryptos avec market cap, volume, prix, etc.
        """
        endpoint = "/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": limit,
            "page": 1,
            "sparkline": sparkline,
            "price_change_percentage": price_change_percentage,
        }
        return self._make_request(endpoint, params)

    def fetch_crypto_details(self, crypto_id: str) -> Dict:
        """
        Récupère les détails d'une cryptomonnaie spécifique.

        Args:
            crypto_id: ID de la cryptomonnaie (ex. "bitcoin", "ethereum").

        Returns:
            Dict: Détails de la cryptomonnaie.
        """
        endpoint = f"/coins/{crypto_id}"
        return self._make_request(endpoint)

    def fetch_global_market_data(self) -> Dict:
        """
        Récupère les données globales du marché crypto.

        Returns:
            Dict: Données globales du marché.
        """
        data = self._make_request("/global")
        return data["data"]
