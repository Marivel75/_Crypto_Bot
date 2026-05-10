"""
Tests du module paper trading : PaperTrader (classe) + endpoints API.
Base SQLite en mémoire, isolée du reste des tests.
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

from unittest.mock import patch

from api.main import app
from api.dependencies import get_db
from src.models.ohlcv import OHLCV, Base as OHLCVBase
from src.models.paper_trade import PaperPortfolio, PaperTrade, Base as PaperTradeBase
from src.paper_trading.paper_trader import PaperTrader


# ---------------------------------------------------------------------------
# Base de données de test
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

OHLCVBase.metadata.create_all(bind=engine)
PaperTradeBase.metadata.create_all(bind=engine)

BTC_PRICE = 65_000.0
ETH_PRICE = 3_000.0


def _seed():
    db = TestingSessionLocal()
    try:
        now = datetime(2026, 4, 1)
        db.add(OHLCV(
            id=str(uuid.uuid4()), timestamp=now, symbol="BTC/USDT",
            timeframe="1d", open=64000.0, high=66000.0, low=63000.0,
            close=BTC_PRICE, volume=1000.0, exchange="binance",
        ))
        db.add(OHLCV(
            id=str(uuid.uuid4()), timestamp=now, symbol="ETH/USDT",
            timeframe="1d", open=2900.0, high=3100.0, low=2800.0,
            close=ETH_PRICE, volume=5000.0, exchange="binance",
        ))
        db.commit()
    finally:
        db.close()


_seed()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def _db_override():
    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    # Neutralise le cache live pour que get_last_price() utilise les bougies OHLCV seedées
    with patch("src.services.live_price_cache.live_price_cache.get", return_value=None):
        yield
    if original is not None:
        app.dependency_overrides[get_db] = original
    else:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def client(_db_override):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def trader(db):
    return PaperTrader(db)


@pytest.fixture()
def portfolio(trader):
    return trader.create_portfolio(name="Test Portfolio", initial_capital=10_000.0)


@pytest.fixture()
def open_trade(trader, portfolio):
    return trader.open_position(
        portfolio_id=portfolio.id,
        symbol="BTC/USDT",
        quantity=0.1,
    )


# ---------------------------------------------------------------------------
# Tests unitaires — PaperTrader
# ---------------------------------------------------------------------------

class TestGetLastPrice:
    def test_returns_correct_close(self, trader):
        price = trader.get_last_price("BTC/USDT")
        assert price == BTC_PRICE

    def test_case_insensitive_symbol(self, trader):
        price = trader.get_last_price("btc/usdt")
        assert price == BTC_PRICE

    def test_unknown_symbol_raises(self, trader):
        with pytest.raises(ValueError, match="Aucune bougie"):
            trader.get_last_price("UNKNOWN/USDT")


class TestCreatePortfolio:
    def test_fields_correct(self, trader):
        p = trader.create_portfolio(name="Mon portefeuille", initial_capital=5_000.0)
        assert p.name == "Mon portefeuille"
        assert p.initial_capital == 5_000.0
        assert p.cash == 5_000.0
        assert p.id is not None

    def test_cash_equals_initial_capital(self, trader):
        p = trader.create_portfolio(name="Zero check", initial_capital=1.0)
        assert p.cash == p.initial_capital


class TestOpenPosition:
    def test_open_by_quantity(self, trader, portfolio):
        trade = trader.open_position(portfolio_id=portfolio.id, symbol="BTC/USDT", quantity=0.1)
        assert trade.status == "OPEN"
        assert trade.side == "BUY"
        assert trade.entry_price == BTC_PRICE
        assert trade.quantity == 0.1
        assert trade.symbol == "BTC/USDT"

    def test_cash_debited(self, trader, portfolio):
        cash_before = portfolio.cash
        trader.open_position(portfolio_id=portfolio.id, symbol="BTC/USDT", quantity=0.1)
        trader.db.refresh(portfolio)
        assert portfolio.cash == pytest.approx(cash_before - 0.1 * BTC_PRICE)

    def test_open_by_amount_usdt(self, trader, portfolio):
        trade = trader.open_position(portfolio_id=portfolio.id, symbol="ETH/USDT", amount_usdt=300.0)
        assert trade.quantity == pytest.approx(300.0 / ETH_PRICE)

    def test_insufficient_cash_raises(self, trader, portfolio):
        with pytest.raises(ValueError, match="Cash insuffisant"):
            trader.open_position(portfolio_id=portfolio.id, symbol="BTC/USDT", quantity=1000.0)

    def test_missing_quantity_and_amount_raises(self, trader, portfolio):
        with pytest.raises(ValueError, match="Fournir quantity ou amount_usdt"):
            trader.open_position(portfolio_id=portfolio.id, symbol="BTC/USDT")

    def test_min_quantity_raises(self, trader, portfolio):
        with pytest.raises(ValueError, match="Quantité minimale"):
            trader.open_position(portfolio_id=portfolio.id, symbol="BTC/USDT", quantity=0.00001)

    def test_unknown_portfolio_raises(self, trader):
        with pytest.raises(ValueError, match="introuvable"):
            trader.open_position(portfolio_id=str(uuid.uuid4()), symbol="BTC/USDT", quantity=0.1)

    def test_unknown_symbol_raises(self, trader, portfolio):
        with pytest.raises(ValueError, match="Aucune bougie"):
            trader.open_position(portfolio_id=portfolio.id, symbol="DOGE/USDT", quantity=1.0)

    def test_signal_source_stored(self, trader, portfolio):
        trade = trader.open_position(
            portfolio_id=portfolio.id, symbol="BTC/USDT", quantity=0.01,
            signal_source="xgboost", signal_score=0.85,
        )
        assert trade.signal_source == "xgboost"
        assert trade.signal_score == pytest.approx(0.85)


class TestClosePosition:
    def test_status_becomes_closed(self, trader, open_trade):
        closed = trader.close_position(open_trade.id)
        assert closed.status == "CLOSED"

    def test_exit_price_is_last_close(self, trader, open_trade):
        closed = trader.close_position(open_trade.id)
        assert closed.exit_price == BTC_PRICE

    def test_pnl_correct_flat_market(self, trader, open_trade):
        # Entrée et sortie au même prix → P&L = 0
        closed = trader.close_position(open_trade.id)
        assert closed.pnl == pytest.approx(0.0)
        assert closed.pnl_pct == pytest.approx(0.0)

    def test_cash_credited(self, trader, portfolio, open_trade):
        cash_after_buy = portfolio.cash
        trader.db.refresh(portfolio)
        cash_before_close = portfolio.cash
        trader.close_position(open_trade.id)
        trader.db.refresh(portfolio)
        assert portfolio.cash == pytest.approx(cash_before_close + open_trade.quantity * BTC_PRICE)

    def test_close_already_closed_raises(self, trader, open_trade):
        trader.close_position(open_trade.id)
        with pytest.raises(ValueError, match="déjà fermée"):
            trader.close_position(open_trade.id)

    def test_unknown_trade_raises(self, trader):
        with pytest.raises(ValueError, match="introuvable"):
            trader.close_position(str(uuid.uuid4()))


class TestGetPortfolioSummary:
    def test_empty_portfolio(self, trader):
        p = trader.create_portfolio(name="Empty", initial_capital=1_000.0)
        summary = trader.get_portfolio_summary(p.id)

        assert summary["metrics"]["total_capital"] == pytest.approx(1_000.0)
        assert summary["metrics"]["total_realized_pnl"] == pytest.approx(0.0)
        assert summary["metrics"]["latent_pnl"] == pytest.approx(0.0)
        assert summary["metrics"]["win_rate"] == pytest.approx(0.0)
        assert summary["metrics"]["total_open_trades"] == 0
        assert summary["metrics"]["total_closed_trades"] == 0
        assert summary["open_positions"] == []
        assert summary["closed_trades"] == []

    def test_open_position_shows_in_summary(self, trader, portfolio, open_trade):
        summary = trader.get_portfolio_summary(portfolio.id)
        assert summary["metrics"]["total_open_trades"] >= 1
        ids = [p["id"] for p in summary["open_positions"]]
        assert open_trade.id in ids

    def test_closed_trade_appears_in_history(self, trader, portfolio, open_trade):
        trader.close_position(open_trade.id)
        summary = trader.get_portfolio_summary(portfolio.id)
        ids = [t["id"] for t in summary["closed_trades"]]
        assert open_trade.id in ids

    def test_unknown_portfolio_raises(self, trader):
        with pytest.raises(ValueError, match="introuvable"):
            trader.get_portfolio_summary(str(uuid.uuid4()))

    def test_win_rate_calculation(self, trader):
        p = trader.create_portfolio(name="WinRate", initial_capital=50_000.0)
        # 2 trades fermés : P&L = 0 pour les deux (flat market)
        t1 = trader.open_position(portfolio_id=p.id, symbol="BTC/USDT", quantity=0.1)
        trader.close_position(t1.id)
        t2 = trader.open_position(portfolio_id=p.id, symbol="BTC/USDT", quantity=0.1)
        trader.close_position(t2.id)
        summary = trader.get_portfolio_summary(p.id)
        # P&L = 0 → ni gagnant ni perdant → win_rate = 0
        assert summary["metrics"]["win_rate"] == pytest.approx(0.0)
        assert summary["metrics"]["total_closed_trades"] == 2


# ---------------------------------------------------------------------------
# Tests d'intégration — API /paper-trading
# ---------------------------------------------------------------------------

class TestPortfoliosAPI:
    def test_create_portfolio_201(self, client):
        r = client.post("/paper-trading/portfolios", json={"name": "API Portfolio", "initial_capital": 10000.0})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "API Portfolio"
        assert data["cash"] == 10000.0
        assert "id" in data

    def test_create_portfolio_zero_capital(self, client):
        r = client.post("/paper-trading/portfolios", json={"name": "Bad", "initial_capital": 0.0})
        assert r.status_code == 422

    def test_create_portfolio_negative_capital(self, client):
        r = client.post("/paper-trading/portfolios", json={"name": "Bad", "initial_capital": -100.0})
        assert r.status_code == 422

    def test_list_portfolios(self, client):
        r = client.get("/paper-trading/portfolios")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_get_portfolio_summary_ok(self, client):
        create = client.post("/paper-trading/portfolios", json={"name": "Summary Test", "initial_capital": 5000.0})
        pid = create.json()["id"]
        r = client.get(f"/paper-trading/portfolios/{pid}")
        assert r.status_code == 200
        data = r.json()
        assert "portfolio" in data
        assert "metrics" in data
        assert "open_positions" in data
        assert "closed_trades" in data

    def test_get_portfolio_summary_404(self, client):
        r = client.get(f"/paper-trading/portfolios/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_portfolio_response_schema(self, client):
        create = client.post("/paper-trading/portfolios", json={"name": "Schema", "initial_capital": 1000.0})
        data = create.json()
        for field in ("id", "name", "initial_capital", "cash", "created_at"):
            assert field in data


class TestOrdersAPI:
    @pytest.fixture(scope="class")
    def portfolio_id(self, client):
        r = client.post("/paper-trading/portfolios", json={"name": "Orders Test", "initial_capital": 100_000.0})
        return r.json()["id"]

    def test_place_order_by_quantity(self, client, portfolio_id):
        r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "BTC/USDT", "quantity": 0.1,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "OPEN"
        assert data["side"] == "BUY"
        assert data["entry_price"] == BTC_PRICE

    def test_place_order_by_amount_usdt(self, client, portfolio_id):
        r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "ETH/USDT", "amount_usdt": 600.0,
        })
        assert r.status_code == 201
        assert r.json()["quantity"] == pytest.approx(600.0 / ETH_PRICE)

    def test_place_order_missing_both_qty(self, client, portfolio_id):
        r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "BTC/USDT",
        })
        assert r.status_code == 422

    def test_place_order_insufficient_cash(self, client, portfolio_id):
        r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "BTC/USDT", "quantity": 9999.0,
        })
        assert r.status_code == 400
        assert "insuffisant" in r.json()["detail"].lower()

    def test_place_order_unknown_symbol(self, client, portfolio_id):
        r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "DOGE/USDT", "quantity": 1.0,
        })
        assert r.status_code == 400

    def test_place_order_unknown_portfolio(self, client):
        r = client.post("/paper-trading/orders", json={
            "portfolio_id": str(uuid.uuid4()), "symbol": "BTC/USDT", "quantity": 0.1,
        })
        assert r.status_code == 400

    def test_close_order_ok(self, client, portfolio_id):
        open_r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "BTC/USDT", "quantity": 0.01,
        })
        trade_id = open_r.json()["id"]
        close_r = client.post(f"/paper-trading/orders/{trade_id}/close")
        assert close_r.status_code == 200
        data = close_r.json()
        assert data["status"] == "CLOSED"
        assert data["exit_price"] == BTC_PRICE
        assert data["pnl"] is not None

    def test_close_order_already_closed(self, client, portfolio_id):
        open_r = client.post("/paper-trading/orders", json={
            "portfolio_id": portfolio_id, "symbol": "BTC/USDT", "quantity": 0.01,
        })
        trade_id = open_r.json()["id"]
        client.post(f"/paper-trading/orders/{trade_id}/close")
        r = client.post(f"/paper-trading/orders/{trade_id}/close")
        assert r.status_code == 400
        assert "fermée" in r.json()["detail"].lower()

    def test_close_order_not_found(self, client):
        r = client.post(f"/paper-trading/orders/{uuid.uuid4()}/close")
        assert r.status_code == 400


class TestListOrdersAPI:
    @pytest.fixture(scope="class")
    def seeded(self, client):
        p = client.post("/paper-trading/portfolios", json={"name": "List Test", "initial_capital": 50_000.0}).json()
        pid = p["id"]
        t1 = client.post("/paper-trading/orders", json={"portfolio_id": pid, "symbol": "BTC/USDT", "quantity": 0.01}).json()
        t2 = client.post("/paper-trading/orders", json={"portfolio_id": pid, "symbol": "ETH/USDT", "quantity": 0.1}).json()
        client.post(f"/paper-trading/orders/{t1['id']}/close")
        return {"portfolio_id": pid, "open_id": t2["id"], "closed_id": t1["id"]}

    def test_list_all(self, client, seeded):
        r = client.get("/paper-trading/orders")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_portfolio(self, client, seeded):
        r = client.get(f"/paper-trading/orders?portfolio_id={seeded['portfolio_id']}")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 2
        assert all(t["portfolio_id"] == seeded["portfolio_id"] for t in data)

    def test_filter_by_status_open(self, client, seeded):
        r = client.get(f"/paper-trading/orders?portfolio_id={seeded['portfolio_id']}&status=OPEN")
        assert r.status_code == 200
        assert all(t["status"] == "OPEN" for t in r.json())

    def test_filter_by_status_closed(self, client, seeded):
        r = client.get(f"/paper-trading/orders?portfolio_id={seeded['portfolio_id']}&status=CLOSED")
        assert r.status_code == 200
        assert all(t["status"] == "CLOSED" for t in r.json())

    def test_filter_by_symbol(self, client, seeded):
        r = client.get(f"/paper-trading/orders?portfolio_id={seeded['portfolio_id']}&symbol=ETH/USDT")
        assert r.status_code == 200
        assert all(t["symbol"] == "ETH/USDT" for t in r.json())

    def test_invalid_status_filter(self, client):
        r = client.get("/paper-trading/orders?status=INVALID")
        assert r.status_code == 422

    def test_limit_respected(self, client):
        r = client.get("/paper-trading/orders?limit=1")
        assert r.status_code == 200
        assert len(r.json()) <= 1

    def test_trade_response_schema(self, client, seeded):
        data = client.get(f"/paper-trading/orders?portfolio_id={seeded['portfolio_id']}&limit=1").json()
        assert len(data) >= 1
        row = data[0]
        for field in ("id", "portfolio_id", "symbol", "side", "quantity", "entry_price",
                      "entry_time", "status", "signal_source", "created_at"):
            assert field in row
