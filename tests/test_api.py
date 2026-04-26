"""
Tests pour l'API FastAPI (routers health, ohlcv, market, signals).
Utilise une base SQLite en mémoire et override la dépendance get_db.
"""

import pytest
import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.dependencies import get_db
from src.models.ohlcv import OHLCV, Base as OHLCVBase
from src.models.ticker import TickerSnapshot, Base as TickerBase
from src.models.market_data_base import MarketDataBase
from src.models.top_crypto_snapshot import TopCryptoSnapshot
from src.models.top_crypto import TopCrypto
from src.models.global_snapshot import GlobalMarketSnapshot
from src.models.global_market_cap import GlobalMarketCap
from src.models.global_market_volume import GlobalMarketVolume
from src.models.global_market_dominance import GlobalMarketDominance


# ---------------------------------------------------------------------------
# Setup base de données de test
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"

# StaticPool : toutes les sessions partagent la même connexion en mémoire
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

OHLCVBase.metadata.create_all(bind=engine)
TickerBase.metadata.create_all(bind=engine)
MarketDataBase.metadata.create_all(bind=engine)


def _make_ohlcv(symbol, timeframe, exchange, timestamp, close=50000.0, idx=0):
    return OHLCV(
        id=str(uuid.uuid4()),
        timestamp=timestamp,
        symbol=symbol,
        timeframe=timeframe,
        open=close - 100 + idx,
        high=close + 200,
        low=close - 200,
        close=close + idx * 10,
        volume=1000.0 + idx,
        price_range=400.0,
        price_change=100.0,
        price_change_pct=0.2,
        date=timestamp.strftime("%Y-%m-%d"),
        exchange=exchange,
    )


def _seed_database():
    session = TestingSessionLocal()
    try:
        now = datetime(2026, 4, 1)

        # 60 bougies BTC/USDT 1d binance (warm-up suffisant pour SMA50)
        for i in range(60):
            session.add(_make_ohlcv(
                "BTC/USDT", "1d", "binance",
                now - timedelta(days=60 - i),
                close=65000.0, idx=i,
            ))

        # Quelques bougies ETH/USDT 1h kraken
        for i in range(10):
            session.add(_make_ohlcv(
                "ETH/USDT", "1h", "kraken",
                now - timedelta(hours=10 - i),
                close=3000.0, idx=i,
            ))

        # Ticker snapshot
        session.add(TickerSnapshot(
            id=str(uuid.uuid4()),
            snapshot_time=now,
            symbol="BTC/USDT",
            exchange="binance",
            price=65000.0,
            volume_24h=42000000.0,
            price_change_24h=500.0,
            price_change_pct_24h=0.77,
            high_24h=66000.0,
            low_24h=64000.0,
        ))

        # Top crypto snapshot
        snap = TopCryptoSnapshot(snapshot_time=now, vs_currency="usd")
        session.add(snap)
        session.flush()
        session.add(TopCrypto(snapshot_id=snap.id, rank=1, crypto_id="bitcoin", symbol="BTC", name="Bitcoin", price=65000.0, market_cap=1.3e12, volume_24h=4.2e10, price_change_pct_24h=0.77))
        session.add(TopCrypto(snapshot_id=snap.id, rank=2, crypto_id="ethereum", symbol="ETH", name="Ethereum", price=3000.0, market_cap=3.6e11, volume_24h=1.5e10, price_change_pct_24h=1.2))

        # Global market snapshot
        gsnap = GlobalMarketSnapshot(
            timestamp=now,
            active_cryptocurrencies=17000,
            markets=900,
            market_cap_change_24h=1.5,
            volume_change_24h=2.3,
        )
        session.add(gsnap)
        session.flush()
        session.add(GlobalMarketCap(snapshot_id=gsnap.id, currency="usd", value=2.3e12))
        session.add(GlobalMarketVolume(snapshot_id=gsnap.id, currency="usd", value=9.8e10))
        session.add(GlobalMarketDominance(snapshot_id=gsnap.id, asset="btc", percentage=54.2))
        session.add(GlobalMarketDominance(snapshot_id=gsnap.id, asset="eth", percentage=12.1))

        session.commit()
    finally:
        session.close()


_seed_database()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_structure(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# Tests /ohlcv
# ---------------------------------------------------------------------------

class TestOHLCV:
    def test_get_all_default_limit(self, client):
        r = client.get("/ohlcv")
        assert r.status_code == 200
        assert len(r.json()) <= 100

    def test_filter_by_symbol(self, client):
        r = client.get("/ohlcv?symbol=BTC/USDT")
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        assert all(row["symbol"] == "BTC/USDT" for row in data)

    def test_filter_by_timeframe(self, client):
        data = client.get("/ohlcv?timeframe=1h").json()
        assert all(row["timeframe"] == "1h" for row in data)

    def test_filter_by_exchange(self, client):
        data = client.get("/ohlcv?exchange=kraken").json()
        assert all(row["exchange"] == "kraken" for row in data)

    def test_limit_respected(self, client):
        r = client.get("/ohlcv?limit=5")
        assert len(r.json()) <= 5

    def test_limit_max_enforced(self, client):
        r = client.get("/ohlcv?limit=9999")
        assert r.status_code == 422

    def test_result_schema(self, client):
        row = client.get("/ohlcv?limit=1").json()[0]
        for field in ("id", "timestamp", "symbol", "timeframe", "open", "high", "low", "close", "volume", "exchange"):
            assert field in row

    def test_ordered_desc_by_timestamp(self, client):
        data = client.get("/ohlcv?symbol=BTC/USDT&limit=10").json()
        timestamps = [row["timestamp"] for row in data]
        assert timestamps == sorted(timestamps, reverse=True)


class TestOHLCVSymbols:
    def test_returns_list(self, client):
        r = client.get("/ohlcv/symbols")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_symbol_schema(self, client):
        data = client.get("/ohlcv/symbols").json()
        assert len(data) > 0
        for row in data:
            assert "symbol" in row
            assert "exchange" in row
            assert "timeframe" in row
            assert "count" in row

    def test_count_is_positive(self, client):
        data = client.get("/ohlcv/symbols").json()
        assert all(row["count"] > 0 for row in data)

    def test_filter_by_exchange(self, client):
        data = client.get("/ohlcv/symbols?exchange=binance").json()
        assert all(row["exchange"] == "binance" for row in data)


class TestOHLCVLatest:
    def test_returns_data(self, client):
        r = client.get("/ohlcv/latest?symbol=BTC/USDT&timeframe=1d")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_default_timeframe_1d(self, client):
        data = client.get("/ohlcv/latest").json()
        assert all(row["timeframe"] == "1d" for row in data)


# ---------------------------------------------------------------------------
# Tests /market
# ---------------------------------------------------------------------------

class TestMarketTop:
    def test_returns_snapshot(self, client):
        r = client.get("/market/top")
        assert r.status_code == 200
        data = r.json()
        assert "snapshot_time" in data
        assert "cryptos" in data

    def test_limit_respected(self, client):
        data = client.get("/market/top?limit=1").json()
        assert len(data["cryptos"]) <= 1

    def test_crypto_schema(self, client):
        cryptos = client.get("/market/top").json()["cryptos"]
        assert len(cryptos) > 0
        for c in cryptos:
            assert "symbol" in c
            assert "rank" in c
            assert "price" in c

    def test_ranked_by_rank(self, client):
        cryptos = client.get("/market/top").json()["cryptos"]
        ranks = [c["rank"] for c in cryptos if c["rank"] is not None]
        assert ranks == sorted(ranks)

    def test_404_unknown_currency(self, client):
        r = client.get("/market/top?currency=XYZ")
        assert r.status_code == 404


class TestMarketGlobal:
    def test_returns_data(self, client):
        r = client.get("/market/global")
        assert r.status_code == 200

    def test_schema(self, client):
        data = client.get("/market/global").json()
        for field in ("snapshot_time", "market_cap_usd", "volume_usd", "dominance"):
            assert field in data

    def test_dominance_list(self, client):
        data = client.get("/market/global").json()
        assert isinstance(data["dominance"], list)
        assert len(data["dominance"]) >= 2
        assert all("asset" in d and "percentage" in d for d in data["dominance"])


class TestMarketTicker:
    def test_returns_list(self, client):
        r = client.get("/market/ticker")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_symbol(self, client):
        data = client.get("/market/ticker?symbol=BTC/USDT").json()
        assert all(row["symbol"] == "BTC/USDT" for row in data)

    def test_ticker_schema(self, client):
        data = client.get("/market/ticker").json()
        assert len(data) > 0
        row = data[0]
        for field in ("symbol", "exchange", "price", "snapshot_time"):
            assert field in row


# ---------------------------------------------------------------------------
# Tests /signals
# ---------------------------------------------------------------------------

class TestSignals:
    def test_symbol_required(self, client):
        r = client.get("/signals")
        assert r.status_code == 422

    def test_returns_data_with_indicators(self, client):
        r = client.get("/signals?symbol=BTC/USDT&timeframe=1d&limit=10")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_indicator_fields_present(self, client):
        data = client.get("/signals?symbol=BTC/USDT&timeframe=1d&limit=10").json()
        row = data[-1]  # Dernière bougie : tous les indicateurs calculés
        for field in ("sma_20", "ema_20", "rsi_14", "macd_line", "bb_upper", "bb_lower"):
            assert field in row

    def test_indicators_are_numbers(self, client):
        data = client.get("/signals?symbol=BTC/USDT&timeframe=1d&limit=10").json()
        row = data[-1]
        assert isinstance(row["sma_20"], float)
        assert isinstance(row["rsi_14"], float)

    def test_404_unknown_symbol(self, client):
        r = client.get("/signals?symbol=UNKNOWN/USDT")
        assert r.status_code == 404

    def test_limit_min_enforced(self, client):
        r = client.get("/signals?symbol=BTC/USDT&limit=3")
        assert r.status_code == 422

    def test_ohlcv_fields_present(self, client):
        data = client.get("/signals?symbol=BTC/USDT&timeframe=1d&limit=10").json()
        row = data[0]
        for field in ("timestamp", "open", "high", "low", "close", "volume"):
            assert field in row
