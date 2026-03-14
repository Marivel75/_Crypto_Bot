# System Architecture — Nouveaux Composants CryptoBot

## Résumé Exécutif

Ce document spécifie l'architecture technique pour quatre nouveaux composants du système CryptoBot :

1. **Paper Trading Engine** — Simulation d'exécution de trades pour évaluer les signaux
2. **Alert System** — Système de notifications via email, Telegram, et in-app
3. **New Collectors** — Extension ETL pour données on-chain et réglementaires
4. **ML Pipeline Extensions** — Environnement RL, modèles LSTM, et clustering

L'architecture maintient les principes fondamentaux : pas d'APIs payantes, asyncio partout, Pydantic v2, type hints stricts, et respect des boundaries d'équipes.

---

## 1. Paper Trading Engine

### 1.1 Rationale & Design Decisions

**Objectif** : Permettre à Noah (trader) de simuler des trades sur les signaux générés sans risque réel.

**Architecture** :
- Nouvelle table `paper_accounts` pour suivi du solde (capital initial + P&L)
- Nouvelle table `paper_positions` pour positions ouvertes
- Nouvelle table `paper_orders` pour ordres en attente (limit/market, SL/TP)
- Nouvelle table `paper_trades` pour trades réalisés (historique complet)
- Service FastAPI `/api/v1/paper-trading/*` pour CRUD
- Worker asynchrone qui écoute les nouveaux candles via TimescaleDB et exécute les ordres

**Constraints** :
- Leverage maximal = 10x (régulation virtuelle)
- Margin safety = 2x (vérification obligatoire)
- Solde minimum = 1 USDT
- Fees = 0.1% maker + 0.1% taker (simulation Binance)
- Pas de slippage (simul. simplifiée)

---

### 1.2 Database Schema (DDL)

```sql
-- Paper trading accounts (simulé, pas réel)
CREATE TABLE paper_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name VARCHAR(100) NOT NULL,
    initial_balance NUMERIC(20, 8) NOT NULL CHECK (initial_balance > 0),
    current_balance NUMERIC(20, 8) NOT NULL,
    pnl_total NUMERIC(20, 8) NOT NULL DEFAULT 0,
    leverage_max INT NOT NULL DEFAULT 10 CHECK (leverage_max BETWEEN 1 AND 10),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, account_name)
);

CREATE INDEX idx_paper_accounts_user ON paper_accounts(user_id);

-- Paper positions (ouvertes)
CREATE TABLE paper_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_account_id UUID NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    quantity NUMERIC(20, 8) NOT NULL CHECK (quantity > 0),
    entry_price NUMERIC(20, 8) NOT NULL CHECK (entry_price > 0),
    current_price NUMERIC(20, 8) NOT NULL CHECK (current_price > 0),
    leverage_used INT NOT NULL DEFAULT 1 CHECK (leverage_used BETWEEN 1 AND 10),
    margin_required NUMERIC(20, 8) NOT NULL CHECK (margin_required > 0),
    unrealized_pnl NUMERIC(20, 8) NOT NULL DEFAULT 0,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(paper_account_id, symbol, side)
);

CREATE INDEX idx_paper_positions_account ON paper_positions(paper_account_id);
CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol);

-- Paper orders (limit/market orders avec SL/TP)
CREATE TABLE paper_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_account_id UUID NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES trading_signals(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT')),
    quantity NUMERIC(20, 8) NOT NULL CHECK (quantity > 0),
    entry_price NUMERIC(20, 8) NOT NULL CHECK (entry_price > 0),
    stop_loss NUMERIC(20, 8),
    take_profit JSONB NOT NULL DEFAULT '[]', -- array of TP levels: [{"level": 1, "price": X, "quantity": Q}]
    leverage INT NOT NULL DEFAULT 1 CHECK (leverage BETWEEN 1 AND 10),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'FILLED', 'CANCELLED', 'REJECTED')),
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_tp_array CHECK (jsonb_array_length(take_profit) <= 5)
);

CREATE INDEX idx_paper_orders_account ON paper_orders(paper_account_id);
CREATE INDEX idx_paper_orders_signal ON paper_orders(signal_id);
CREATE INDEX idx_paper_orders_status ON paper_orders(status);

-- Paper trades (historique)
CREATE TABLE paper_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_account_id UUID NOT NULL REFERENCES paper_accounts(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES paper_orders(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    quantity NUMERIC(20, 8) NOT NULL CHECK (quantity > 0),
    entry_price NUMERIC(20, 8) NOT NULL,
    exit_price NUMERIC(20, 8),
    leverage INT NOT NULL,
    pnl NUMERIC(20, 8), -- actualizado quando fechado
    pnl_percent NUMERIC(10, 4),
    fees_paid NUMERIC(20, 8) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'LIQUIDATED')),
    exit_reason VARCHAR(50), -- 'TP', 'SL', 'MANUAL', 'LIQUIDATION'
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_paper_trades_account ON paper_trades(paper_account_id);
CREATE INDEX idx_paper_trades_symbol ON paper_trades(symbol);
CREATE INDEX idx_paper_trades_status ON paper_trades(status);
CREATE INDEX idx_paper_trades_dates ON paper_trades(opened_at, closed_at);
```

---

### 1.3 Pydantic Models (src/shared/models/paper_trading.py)

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PaperAccountCreate(BaseModel):
    """Input model for creating a paper account."""
    account_name: str = Field(..., min_length=1, max_length=100)
    initial_balance: Decimal = Field(..., gt=0)
    leverage_max: int = Field(default=10, ge=1, le=10)


class PaperAccountRead(BaseModel):
    """Response model for paper account."""
    id: UUID
    user_id: UUID
    account_name: str
    initial_balance: Decimal
    current_balance: Decimal
    pnl_total: Decimal
    leverage_max: int
    created_at: datetime
    updated_at: datetime


class PaperOrderCreate(BaseModel):
    """Input model for creating a paper order."""
    signal_id: UUID | None = None
    symbol: str = Field(..., min_length=2, max_length=20)
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    quantity: Decimal = Field(..., gt=0)
    entry_price: Decimal = Field(..., gt=0)
    stop_loss: Decimal | None = Field(None, gt=0)
    take_profit: list[dict] = Field(
        default_factory=list,
        description='Array of TP levels: [{"level": 1, "price": X, "quantity": Q}]'
    )
    leverage: int = Field(default=1, ge=1, le=10)

    @field_validator("quantity", "entry_price", "leverage")
    @classmethod
    def validate_order_params(cls, v: Decimal | int) -> Decimal | int:
        """Validate order parameters."""
        return v


class PaperOrderRead(BaseModel):
    """Response model for paper order."""
    id: UUID
    paper_account_id: UUID
    signal_id: UUID | None
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    quantity: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: list[dict]
    leverage: int
    status: Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"]
    rejection_reason: str | None
    created_at: datetime
    filled_at: datetime | None


class PaperTradeRead(BaseModel):
    """Response model for paper trade."""
    id: UUID
    paper_account_id: UUID
    order_id: UUID
    symbol: str
    side: Literal["LONG", "SHORT"]
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal | None
    leverage: int
    pnl: Decimal | None
    pnl_percent: Decimal | None
    fees_paid: Decimal
    status: Literal["OPEN", "CLOSED", "LIQUIDATED"]
    exit_reason: str | None
    opened_at: datetime
    closed_at: datetime | None
```

---

### 1.4 FastAPI Endpoints

```
POST   /api/v1/paper-trading/accounts
       → Create a new paper trading account
       Request: PaperAccountCreate
       Response: ApiResponse[PaperAccountRead]

GET    /api/v1/paper-trading/accounts/{account_id}
       → Get account details with current balance/P&L
       Response: ApiResponse[PaperAccountRead]

GET    /api/v1/paper-trading/accounts/{account_id}/positions
       → List open positions for the account
       Query: symbol (optional), limit, page
       Response: ApiResponse[list[PaperPositionRead]]

GET    /api/v1/paper-trading/accounts/{account_id}/trades
       → Get closed + open trades
       Query: symbol (optional), status, limit, page
       Response: ApiResponse[list[PaperTradeRead]]

GET    /api/v1/paper-trading/accounts/{account_id}/performance
       → Get aggregate P&L, win rate, Sharpe ratio
       Response: ApiResponse[PerformanceMetrics]

POST   /api/v1/paper-trading/orders
       → Place a new order
       Request: PaperOrderCreate
       Response: ApiResponse[PaperOrderRead]

PUT    /api/v1/paper-trading/orders/{order_id}/cancel
       → Cancel a pending order
       Response: ApiResponse[PaperOrderRead]

GET    /api/v1/paper-trading/orders/{order_id}/status
       → Get order status (useful for polling)
       Response: ApiResponse[PaperOrderRead]
```

---

### 1.5 Paper Trading Service (src/api/services/paper_trading_service.py)

**Key Responsibilities** :
- Create/read paper accounts
- Place orders with validation (margin, leverage, funds)
- Calculate unrealized P&L per position
- Expose performance metrics (total P&L, Sharpe, win rate)

**Validation Rules** :
1. Margin required = (quantity * entry_price / leverage) * 1.5
2. Margin available = current_balance - sum(margin_required for all positions)
3. Reject order if margin required > margin available
4. Reject order if leverage > leverage_max
5. Fees = 0.1% of notional value on entry + exit
6. Max 50 open positions per account

---

### 1.6 Paper Trading Worker (src/api/workers/paper_trading_executor.py)

**Trigger** : Every time a new candle arrives in `crypto_prices`, check all open orders for this symbol.

**Algorithm** :
```
For each paper_account:
  For each open position with symbol:
    current_price = latest candle close
    pnl = (current_price - entry_price) * quantity

    if pnl <= stop_loss * quantity:  # SL hit
      close position, mark trade CLOSED with exit_reason='SL'
      add fees, update account balance, update account P&L

    for each TP level in take_profit:
      if current_price >= tp_level['price']:  # TP hit
        close partial position (tp_level['quantity'])
        mark partial trade CLOSED with exit_reason='TP'
        update account

    if pnl >= liquidation_margin:  # leveraged liquidation
      close position, mark trade LIQUIDATED
      update account balance
```

**Deployment** : Async task in `ml-worker` or separate `paper-trading-worker` container (APScheduler).

---

## 2. Alert System

### 2.1 Rationale & Design Decisions

**Objectif** : Notify all users (Noah, Sarah, Aleksandar) via email, Telegram, or in-app when conditions are met.

**Channels** :
- **Email** : SMTP (Gmail, SendGrid, Mailgun) for regulatory/important alerts
- **Telegram** : Bot API for instant mobile notifications
- **In-App** : WebSocket push (optional) or polling via `/api/v1/alerts/my-alerts`

**Alert Types** :
- New signal (BUY/SELL)
- Price breaches (>10% move)
- Portfolio position: realized loss >5%
- Regulatory news (ESMA, SEC)
- Custom rules (user-defined)

---

### 2.2 Database Schema (DDL)

```sql
-- Alert rules (user-defined + system defaults)
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL CHECK (
        rule_type IN ('SIGNAL', 'PRICE', 'NEWS', 'PORTFOLIO', 'CUSTOM')
    ),
    condition JSONB NOT NULL, -- e.g. {"event": "BUY", "symbol": "BTCUSDT", "confidence_min": 0.7}
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    channels JSONB NOT NULL DEFAULT '["email"]', -- ["email", "telegram", "in_app"]
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, rule_name)
);

CREATE INDEX idx_alert_rules_user ON alert_rules(user_id);
CREATE INDEX idx_alert_rules_enabled ON alert_rules(enabled);

-- Alert history (audit trail)
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_event JSONB NOT NULL, -- e.g. {"signal_id": "...", "symbol": "BTCUSDT", "direction": "BUY"}
    alert_content TEXT NOT NULL,
    channels_sent JSONB NOT NULL, -- ["email", "telegram"]
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'SENT' CHECK (status IN ('SENT', 'FAILED', 'BOUNCED')),
    error_message TEXT
);

CREATE INDEX idx_alert_history_user ON alert_history(user_id);
CREATE INDEX idx_alert_history_sent ON alert_history(sent_at);
CREATE INDEX idx_alert_history_status ON alert_history(status);
```

---

### 2.3 Pydantic Models (src/shared/models/alerts.py)

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    """Input for creating an alert rule."""
    rule_name: str = Field(..., min_length=1, max_length=100)
    rule_type: Literal["SIGNAL", "PRICE", "NEWS", "PORTFOLIO", "CUSTOM"]
    condition: dict = Field(...)  # {"event": "BUY", "symbol": "BTCUSDT", ...}
    enabled: bool = True
    channels: list[Literal["email", "telegram", "in_app"]] = Field(
        default=["email"],
        min_length=1
    )


class AlertRuleRead(BaseModel):
    """Response model for alert rule."""
    id: UUID
    user_id: UUID
    rule_name: str
    rule_type: Literal["SIGNAL", "PRICE", "NEWS", "PORTFOLIO", "CUSTOM"]
    condition: dict
    enabled: bool
    channels: list[str]
    created_at: datetime
    updated_at: datetime


class AlertHistoryRead(BaseModel):
    """Response model for alert event."""
    id: UUID
    alert_rule_id: UUID
    user_id: UUID
    trigger_event: dict
    alert_content: str
    channels_sent: list[str]
    sent_at: datetime
    status: Literal["SENT", "FAILED", "BOUNCED"]
    error_message: str | None
```

---

### 2.4 FastAPI Endpoints

```
POST   /api/v1/alerts/rules
       → Create a new alert rule
       Request: AlertRuleCreate
       Response: ApiResponse[AlertRuleRead]

GET    /api/v1/alerts/rules
       → List all rules for current user
       Query: enabled (optional), rule_type (optional), limit, page
       Response: ApiResponse[list[AlertRuleRead]]

GET    /api/v1/alerts/rules/{rule_id}
       → Get rule details
       Response: ApiResponse[AlertRuleRead]

PUT    /api/v1/alerts/rules/{rule_id}
       → Update rule (condition, channels, enabled)
       Request: AlertRuleCreate
       Response: ApiResponse[AlertRuleRead]

DELETE /api/v1/alerts/rules/{rule_id}
       → Delete rule (soft delete: set enabled=false)
       Response: ApiResponse[dict]

GET    /api/v1/alerts/history
       → Get alert history for current user
       Query: rule_id (optional), status (optional), limit, page
       Response: ApiResponse[list[AlertHistoryRead]]

GET    /api/v1/alerts/my-alerts
       → Get unread in-app alerts (polling endpoint)
       Query: unread_only (default=true), limit=50
       Response: ApiResponse[list[AlertHistoryRead]]

POST   /api/v1/alerts/read/{alert_id}
       → Mark alert as read (in-app)
       Response: ApiResponse[dict]
```

---

### 2.5 Alert Service (src/api/services/alert_service.py)

**Key Responsibilities** :
- CRUD on alert rules
- Match incoming signals/events against rules
- Format alert messages (email, Telegram, in-app)
- Send via SMTP / Telegram Bot API
- Log to alert_history

**Configuration** (src/shared/config.py additions) :
```python
# SMTP (for email alerts)
smtp_server: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_user: str = "your-email@gmail.com"
smtp_password: str = "your-app-password"

# Telegram Bot
telegram_bot_token: str = ""  # Optional; leave empty to disable
telegram_bot_api_url: str = "https://api.telegram.org/bot{token}/sendMessage"

# Alert thresholds
alert_price_change_threshold: float = 0.10  # 10%
alert_portfolio_loss_threshold: float = 0.05  # 5%
```

---

### 2.6 Alert Worker (src/api/workers/alert_evaluator.py)

**Trigger** : Every new signal or price update.

**Algorithm** :
```
For each enabled alert rule in alert_rules:
  condition = rule.condition

  if rule.rule_type == "SIGNAL":
    if new_signal matches condition (symbol, direction, confidence_min):
      send alert

  elif rule.rule_type == "PRICE":
    if price movement >= threshold:
      send alert

  elif rule.rule_type == "NEWS":
    if article sentiment or keywords match condition:
      send alert

  elif rule.rule_type == "PORTFOLIO":
    if position loss >= threshold:
      send alert

  log to alert_history
```

---

## 3. New Collectors (Extension ETL)

### 3.1 Rationale & Design Decisions

**Objectif** : Extend ETL with on-chain data, regulatory feeds, and news sources.

**New Sources** :
- **On-Chain** : Blockchain.com API (free tier), Etherscan API (free tier)
- **Regulatory** : ESMA RSS, SEC RSS, EU Blockchain Observatory
- **News** : BeautifulSoup scraper for Phoenix, Cryptorank RSS
- **Metrics** : Glassnode-like metrics from free sources (limited)

**Architecture** : New collector modules in `src/etl/collectors/` + existing loader pipeline.

---

### 3.2 New Collector Modules

```
src/etl/collectors/
├── blockchain_collector.py      # On-chain data (BTC/ETH only)
├── etherscan_collector.py        # Ethereum-specific (gas, tx count)
├── regulatory_collector.py       # ESMA, SEC feeds
├── news_scraper.py              # BeautifulSoup generic scraper
├── phoenix_news_collector.py     # PhoenixNews RSS
├── cryptorank_collector.py       # Cryptorank RSS
└── metrics_aggregator.py         # Aggregate metrics into signals
```

---

### 3.3 Database Schema Extensions (DDL)

```sql
-- On-chain metrics (BTC/ETH focus)
CREATE TABLE onchain_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL CHECK (symbol IN ('BTC', 'ETH')),
    metric_type VARCHAR(50) NOT NULL CHECK (
        metric_type IN ('WHALE_TRANSACTION', 'NETWORK_ACTIVE', 'MINER_REVENUE',
                       'GAS_PRICE', 'BURN_RATE', 'STAKING_RATIO')
    ),
    metric_value NUMERIC(20, 8) NOT NULL,
    metric_unit VARCHAR(50), -- "USD", "ETH", "gwei", "%" etc
    source VARCHAR(100) NOT NULL, -- "blockchain_com", "etherscan", "glassnode"
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_onchain_metrics_symbol ON onchain_metrics(symbol);
CREATE INDEX idx_onchain_metrics_type ON onchain_metrics(metric_type);
CREATE INDEX idx_onchain_metrics_collected ON onchain_metrics(collected_at);

-- Regulatory documents / alerts
CREATE TABLE regulatory_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100) NOT NULL, -- "ESMA", "SEC", "EU_BLOCKCHAIN"
    jurisdiction VARCHAR(50),
    impact_level VARCHAR(20) CHECK (impact_level IN ('LOW', 'MEDIUM', 'HIGH')),
    url VARCHAR(1000),
    published_at TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_regulatory_alerts_source ON regulatory_alerts(source);
CREATE INDEX idx_regulatory_alerts_published ON regulatory_alerts(published_at);
CREATE INDEX idx_regulatory_alerts_impact ON regulatory_alerts(impact_level);
```

---

### 3.4 New Pydantic Models (src/shared/models/collectors.py)

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OnChainMetric(BaseModel):
    """On-chain metric (BTC/ETH)."""
    id: UUID
    symbol: Literal["BTC", "ETH"]
    metric_type: str  # WHALE_TRANSACTION, NETWORK_ACTIVE, etc
    metric_value: Decimal
    metric_unit: str
    source: str
    collected_at: datetime


class RegulatoryAlert(BaseModel):
    """Regulatory alert from ESMA, SEC, etc."""
    id: UUID
    title: str
    content: str
    source: Literal["ESMA", "SEC", "EU_BLOCKCHAIN"]
    jurisdiction: str | None
    impact_level: Literal["LOW", "MEDIUM", "HIGH"]
    url: str | None
    published_at: datetime | None
    collected_at: datetime
```

---

### 3.5 Collector Implementation Pattern (Example: Etherscan)

```python
# src/etl/collectors/etherscan_collector.py

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EtherscanCollector:
    """Free tier: gas price, transaction count, active addresses."""

    BASE_URL = "https://api.etherscan.io/api"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key  # Optional; free tier = rate limit 5 calls/sec

    async def fetch_gas_price(self) -> dict[str, Any] | None:
        """Fetch current gas price in gwei."""
        params = {
            "module": "gastracker",
            "action": "gasprices",
            "apikey": self.api_key or "YourApiKeyToken",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(self.BASE_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if data["status"] == "1":
                    return {
                        "metric_type": "GAS_PRICE",
                        "metric_value": Decimal(data["result"]["SafeGasPrice"]),
                        "metric_unit": "gwei",
                        "symbol": "ETH",
                        "source": "etherscan",
                    }
            except Exception as e:
                logger.error("Etherscan gas price fetch failed: %s", e)

        return None

    async def fetch_network_stats(self) -> list[dict[str, Any]]:
        """Fetch transaction count, active addresses."""
        # Similar pattern: make API call, parse response, return metrics list
        pass
```

---

### 3.6 BeautifulSoup News Scraper (Generic)

```python
# src/etl/collectors/news_scraper.py

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NewsScraperConfig:
    """Configuration for a news scraper."""
    url: str
    selectors: dict[str, str]  # {"title": "h1.article-title", "content": "div.body"}
    date_format: str | None


async def scrape_news(config: NewsScraperConfig, max_items: int = 20) -> list[dict]:
    """Generic BeautifulSoup scraper."""
    articles = []

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(config.url, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.select("article")[:max_items]:
                title_elem = item.select_one(config.selectors["title"])
                content_elem = item.select_one(config.selectors["content"])
                date_elem = item.select_one(config.selectors.get("date"))

                articles.append({
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "content": content_elem.get_text(strip=True) if content_elem else "",
                    "published_at": (
                        datetime.fromisoformat(date_elem.get("datetime"))
                        if date_elem else None
                    ),
                    "source": config.url,
                })
        except Exception as e:
            logger.error("News scraper failed for %s: %s", config.url, e)

    return articles
```

---

### 3.7 Integration with Existing ETL

**APScheduler jobs** (in `src/etl/__main__.py`) :

```python
scheduler.add_job(
    etherscan_collector.fetch_gas_price,
    "interval",
    minutes=15,
    id="etherscan_gas_price",
)

scheduler.add_job(
    blockchain_collector.fetch_whale_transactions,
    "interval",
    minutes=30,
    id="blockchain_whales",
)

scheduler.add_job(
    regulatory_collector.fetch_esma_alerts,
    "cron",
    hour=9,  # daily at 9 AM
    id="regulatory_daily",
)

for source_config in NEWS_SCRAPER_CONFIGS:  # Phoenix, Cryptorank
    scheduler.add_job(
        scrape_news,
        "interval",
        minutes=60,
        args=(source_config,),
        id=f"news_{source_config.name}",
    )
```

---

## 4. ML Pipeline Extensions

### 4.1 Rationale & Design Decisions

**Objectif** : Phase 2 ML — Supervised learning + optional RL environment.

**Phase 1 Status** : Rules engine + MLflow + walk-forward backtesting.

**Phase 2 Components** :
- **RL Environment** : Gymnasium-compatible environment for paper trading
- **LSTM Model** : PyTorch LSTM for next-step price prediction
- **Clustering** : K-means or Gaussian Mixture Model for regime detection

---

### 4.2 RL Environment (Gymnasium)

```python
# src/ml/environments/trading_env.py

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

logger = logging.getLogger(__name__)


class CryptoPaperTradingEnv(gym.Env):
    """Gymnasium-compatible environment for paper trading RL.

    Action space: {0=HOLD, 1=BUY, 2=SELL}
    Observation: [price, rsi, bb_upper, bb_lower, portfolio_balance, position_size]
    Reward: realized_pnl - fees
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        symbol: str,
        historical_data: np.ndarray,  # shape (T, 6): OHLCV + volume
        initial_balance: float = 10000.0,
        leverage: int = 1,
        fee_rate: float = 0.001,
    ) -> None:
        self.symbol = symbol
        self.historical_data = historical_data
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.fee_rate = fee_rate

        # Gym spaces
        self.action_space = spaces.Discrete(3)  # HOLD, BUY, SELL
        self.observation_space = spaces.Box(
            low=0, high=np.inf, shape=(6,), dtype=np.float32
        )

        # State
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0.0  # BTC quantity
        self.entry_price = 0.0
        self.done = False

    def reset(self, seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        """Reset environment."""
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.done = False

        obs = self._get_observation()
        return obs, {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Execute one step."""
        if self.current_step >= len(self.historical_data) - 1:
            self.done = True
            return self._get_observation(), 0.0, self.done, False, {}

        current_price = Decimal(str(self.historical_data[self.current_step, 4]))  # close
        next_price = Decimal(str(self.historical_data[self.current_step + 1, 4]))

        reward = 0.0

        if action == 1:  # BUY
            if self.balance > 0:
                notional = self.balance / self.leverage
                self.position = float(notional) / float(current_price)
                self.entry_price = float(current_price)
                self.balance -= float(notional * Decimal(str(self.fee_rate)))

        elif action == 2:  # SELL
            if self.position > 0:
                exit_notional = self.position * float(next_price)
                pnl = exit_notional - (self.position * self.entry_price)
                fees = exit_notional * self.fee_rate
                self.balance += pnl - fees
                reward = pnl - fees
                self.position = 0.0

        self.current_step += 1
        self.done = self.current_step >= len(self.historical_data) - 1

        obs = self._get_observation()
        return obs, reward, self.done, False, {}

    def _get_observation(self) -> np.ndarray:
        """Get current observation."""
        if self.current_step >= len(self.historical_data):
            return np.zeros(6, dtype=np.float32)

        candle = self.historical_data[self.current_step]
        price = candle[4]  # close

        return np.array(
            [
                price,           # current price
                0.0,             # RSI (compute externally)
                candle[2],       # high (proxy for BB upper)
                candle[3],       # low (proxy for BB lower)
                self.balance,    # portfolio balance
                self.position,   # position size
            ],
            dtype=np.float32,
        )
```

---

### 4.3 LSTM Model (PyTorch)

```python
# src/ml/models/lstm_predictor.py

from __future__ import annotations

import logging

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class LSTMPredictor(nn.Module):
    """LSTM for next-step price prediction.

    Input: (batch, seq_len, input_size) = (B, 60, 6)  [OHLCV + indicators]
    Output: (batch, 1) = next price or direction
    """

    def __init__(
        self,
        input_size: int = 6,  # OHLCV + one indicator
        hidden_size: int = 64,
        num_layers: int = 2,
        output_size: int = 1,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, output_size),
            nn.Sigmoid(),  # Output: [0, 1] for probability
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]  # Take last timestep
        return self.fc(last_hidden)

    @staticmethod
    def train_epoch(
        model: LSTMPredictor,
        train_loader: torch.utils.data.DataLoader,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
        device: torch.device,
    ) -> float:
        """Train one epoch."""
        model.train()
        total_loss = 0.0

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        return total_loss / len(train_loader)
```

---

### 4.4 Clustering Pipeline (Regime Detection)

```python
# src/ml/pipelines/regime_clustering.py

from __future__ import annotations

import logging

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class RegimeClusterer:
    """Detect market regimes using K-means on price + volatility."""

    def __init__(self, n_regimes: int = 3) -> None:
        self.n_regimes = n_regimes
        self.scaler = StandardScaler()
        self.kmeans = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
        self.regime_labels = {
            0: "BULL",
            1: "SIDEWAYS",
            2: "BEAR",
        }

    def fit(self, prices: np.ndarray, volumes: np.ndarray) -> RegimeClusterer:
        """Fit clustering on price & volatility features."""
        # Feature engineering
        returns = np.diff(prices) / prices[:-1]  # log returns
        volatility = np.std(returns)

        X = np.column_stack([
            prices[:-1],
            returns,
            volumes[:-1] / np.mean(volumes),
        ])

        X_scaled = self.scaler.fit_transform(X)
        self.kmeans.fit(X_scaled)

        logger.info("Regime clustering fitted: %d regimes", self.n_regimes)
        return self

    def predict_regime(self, recent_prices: np.ndarray, recent_volumes: np.ndarray) -> str:
        """Predict current regime."""
        if len(recent_prices) < 2:
            return "UNKNOWN"

        returns = np.diff(recent_prices) / recent_prices[:-1]

        X = np.array([
            [recent_prices[-1], returns[-1], recent_volumes[-1]],
        ])

        X_scaled = self.scaler.transform(X)
        regime_idx = self.kmeans.predict(X_scaled)[0]

        return self.regime_labels.get(regime_idx, "UNKNOWN")
```

---

### 4.5 Integration with SignalGenerator

Update `src/ml/signal_generator.py` to support:

```python
def generate_with_rl_feedback(
    self,
    symbol: str,
    indicators: dict[str, Any],
    rl_action: int | None = None,
    regime: str | None = None,
) -> TradingSignal | None:
    """Generate signal, optionally incorporating RL feedback & regime.

    RL action: 0=HOLD, 1=BUY, 2=SELL (from policy network)
    Regime: "BULL", "SIDEWAYS", "BEAR" (from clustering)
    """
    # Existing rule engine + ML logic
    base_signal = self.generate(symbol, indicators)

    if base_signal is None:
        return None

    # Adjust confidence by RL feedback
    if rl_action is not None and rl_action != 0:
        if (rl_action == 1 and base_signal.signal_type == "BUY") or \
           (rl_action == 2 and base_signal.signal_type == "SELL"):
            # RL agrees with signal — boost confidence
            base_signal.confidence_score = min(
                0.95,
                base_signal.confidence_score * 1.1
            )

    # Regime-based adjustment
    if regime == "BULL" and base_signal.signal_type == "BUY":
        base_signal.confidence_score *= 1.05
    elif regime == "BEAR" and base_signal.signal_type == "SELL":
        base_signal.confidence_score *= 1.05

    return base_signal
```

---

## 5. Component Integration Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES (Existing)                  │
│  [Binance] [CoinGecko] [CCXT] [News RSS] [Fear & Greed]   │
│  + NEW: [Blockchain.com] [Etherscan] [ESMA/SEC] [News]   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────v─────────────────┐
        │   ETL PIPELINE (Extended)      │
        │ ├─ collectors/ (new sources)   │
        │ ├─ transformers/               │
        │ └─ loaders/                    │
        │   APScheduler jobs             │
        └──────────────┬──────────────────┘
                       │
        ┌──────────────v─────────────────────┐
        │   TimescaleDB + MinIO              │
        │ • crypto_prices (existing)         │
        │ • indicators                       │
        │ • trading_signals                  │
        │ • signal_outcomes                  │
        │ + NEW:                             │
        │ • onchain_metrics                  │
        │ • regulatory_alerts                │
        │ • paper_accounts, positions, etc.  │
        │ • alert_rules, alert_history       │
        └──────────────┬──────────────────────┘
                       │
        ┌──────────┬───┴────┬──────────┬─────────┐
        │          │        │          │         │
    ┌───v──┐ ┌────v──┐ ┌──v──┐ ┌────v──┐ ┌──v──┐
    │ ML   │ │Paper  │ │Alert│ │New    │ │ RL  │
    │Engine│ │Trading│ │Syst │ │Coll.  │ │Env  │
    │ (v2) │ │Exec   │ │Eval │ │Integ. │ │+    │
    │      │ │       │ │     │ │       │ │LSTM │
    └───┬──┘ └───┬───┘ └──┬──┘ └───┬───┘ └──┬──┘
        │        │        │        │       │
        │        │        │        │       └─→ [MLflow]
        │        │        │        │
        └────┬───┴────┬───┴────┬───┘
             │        │        │
        ┌────v────────v────────v─────┐
        │   FastAPI Backend           │
        │ ├─ routers/auth             │
        │ ├─ routers/crypto           │
        │ ├─ routers/signals          │
        │ ├─ routers/paper_trading ◄─ NEW
        │ ├─ routers/alerts ◄────────── NEW
        │ ├─ routers/news             │
        │ └─ routers/portfolio        │
        │                             │
        │ ├─ services/                │
        │ ├─ workers/                 │
        │ ├─ dependencies/            │
        └────┬────────────────────────┘
             │
        ┌────v──────────────────┐
        │  Streamlit Frontend    │
        │ ├─ pages/dashboard     │
        │ ├─ pages/veille        │
        │ ├─ pages/portfolio      │
        │ ├─ pages/analytics      │
        │ ├─ pages/performance    │
        │ └─ pages/alerts ◄──── NEW
        └───────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           Docker Compose Services                           │
├─────────────────────────────────────────────────────────────┤
│ • timescaledb, minio, mlflow (existing)                    │
│ • api (FastAPI)                                             │
│ • frontend (Streamlit)                                      │
│ • etl-worker (APScheduler)                                 │
│ • ml-worker (Signal generator + paper trading executor)    │
│ • alert-worker (Optional: separate container)              │
│ • nginx, prometheus, grafana                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Configuration Changes (src/shared/config.py)

```python
# New environment variables for components

# ─────────────────────────────────────────────────────
# PAPER TRADING ENGINE
# ─────────────────────────────────────────────────────
paper_trading_enabled: bool = True
paper_trading_fee_rate: float = 0.001  # 0.1% per trade
paper_trading_max_positions: int = 50
paper_trading_max_leverage: int = 10
paper_trading_min_balance: Decimal = Decimal("1.00")

# ─────────────────────────────────────────────────────
# ALERT SYSTEM
# ─────────────────────────────────────────────────────
alert_system_enabled: bool = True

# SMTP Configuration
smtp_server: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_user: str = ""  # Leave empty to disable email alerts
smtp_password: str = ""
smtp_from_address: str = "alerts@cryptobot.local"

# Telegram Configuration
telegram_bot_token: str = ""  # Leave empty to disable Telegram
telegram_api_url: str = "https://api.telegram.org/bot"

# Alert thresholds
alert_price_change_threshold: float = 0.10  # 10%
alert_portfolio_loss_threshold: float = 0.05  # 5%
alert_confidence_threshold: Decimal = Decimal("0.60")

# ─────────────────────────────────────────────────────
# NEW COLLECTORS
# ─────────────────────────────────────────────────────
blockchain_com_api_key: str = ""  # Optional for rate limit increase
etherscan_api_key: str = ""  # Optional for rate limit increase
enable_onchain_collectors: bool = True
enable_regulatory_collectors: bool = True
enable_news_scrapers: bool = True

# ─────────────────────────────────────────────────────
# ML PIPELINE EXTENSIONS
# ─────────────────────────────────────────────────────
ml_lstm_enabled: bool = True
ml_rl_env_enabled: bool = False  # Phase 2+
ml_regime_clustering_enabled: bool = True
ml_regime_update_frequency_minutes: int = 60
```

---

## 7. Modified ORM Models (src/shared/db_models.py)

Add relationships in `UserOrm`:

```python
class UserOrm(Base):
    # ... existing fields ...

    paper_accounts: Mapped[list[PaperAccountOrm]] = relationship(
        "PaperAccountOrm", back_populates="user", cascade="all, delete-orphan"
    )
    alert_rules: Mapped[list[AlertRuleOrm]] = relationship(
        "AlertRuleOrm", back_populates="user", cascade="all, delete-orphan"
    )
    alert_history: Mapped[list[AlertHistoryOrm]] = relationship(
        "AlertHistoryOrm", back_populates="user", cascade="all, delete-orphan"
    )
```

---

## 8. New ORM Classes (src/shared/db_models.py additions)

```python
# Paper Trading ORM classes
class PaperAccountOrm(Base):
    __tablename__ = "paper_accounts"
    __table_args__ = (UniqueConstraint("user_id", "account_name", name="uq_paper_accounts_user_name"),)

    id: Column = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Column = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_name: Column = Column(String(100), nullable=False)
    initial_balance: Column = Column(Numeric(20, 8), nullable=False)
    current_balance: Column = Column(Numeric(20, 8), nullable=False)
    pnl_total: Column = Column(Numeric(20, 8), nullable=False, server_default="0")
    leverage_max: Column = Column(Integer, nullable=False, server_default="10")
    created_at: Column = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at: Column = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")

    user: Mapped[UserOrm] = relationship("UserOrm", back_populates="paper_accounts")


class PaperOrderOrm(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (
        Index("idx_paper_orders_account", "paper_account_id"),
        Index("idx_paper_orders_status", "status"),
    )

    id: Column = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_account_id: Column = Column(UUID(as_uuid=True), ForeignKey("paper_accounts.id", ondelete="CASCADE"))
    signal_id: Column = Column(UUID(as_uuid=True), ForeignKey("trading_signals.id", ondelete="SET NULL"))
    symbol: Column = Column(String(20), nullable=False)
    side: Column = Column(String(10), nullable=False)
    order_type: Column = Column(String(20), nullable=False)
    quantity: Column = Column(Numeric(20, 8), nullable=False)
    entry_price: Column = Column(Numeric(20, 8), nullable=False)
    stop_loss: Column = Column(Numeric(20, 8))
    take_profit: Column = Column(JSONB, nullable=False, server_default="[]")
    leverage: Column = Column(Integer, nullable=False, server_default="1")
    status: Column = Column(String(20), nullable=False, server_default="PENDING")
    created_at: Column = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    filled_at: Column = Column(DateTime(timezone=True))


class AlertRuleOrm(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (UniqueConstraint("user_id", "rule_name", name="uq_alert_rules_user_name"),)

    id: Column = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Column = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    rule_name: Column = Column(String(100), nullable=False)
    rule_type: Column = Column(String(50), nullable=False)
    condition: Column = Column(JSONB, nullable=False)
    enabled: Column = Column(Boolean, nullable=False, server_default="true")
    channels: Column = Column(JSONB, nullable=False, server_default='["email"]')
    created_at: Column = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at: Column = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")

    user: Mapped[UserOrm] = relationship("UserOrm", back_populates="alert_rules")
```

---

## 9. Implementation Roadmap

### Phase 1 (Weeks 1-2): Paper Trading Engine
- [ ] Implement database schema & migrations
- [ ] Implement Pydantic models & FastAPI endpoints
- [ ] Implement paper trading service (CRUD + validation)
- [ ] Implement paper trading executor worker
- [ ] Add unit tests (80%+ coverage)
- [ ] Integrate with existing signal pipeline

### Phase 2 (Weeks 3-4): Alert System
- [ ] Implement database schema
- [ ] Implement alert service (CRUD rules, evaluation)
- [ ] Implement SMTP sender
- [ ] Implement Telegram bot sender
- [ ] Implement alert evaluator worker
- [ ] Add UI integration in Streamlit

### Phase 3 (Weeks 5-6): New Collectors
- [ ] Implement Etherscan collector
- [ ] Implement Blockchain.com collector
- [ ] Implement regulatory collector (RSS parsing)
- [ ] Implement BeautifulSoup scraper
- [ ] Add APScheduler jobs for each collector
- [ ] Integrate with database loaders

### Phase 4 (Weeks 7-8): ML Extensions
- [ ] Implement LSTM model + training pipeline
- [ ] Implement regime clustering
- [ ] Integrate with SignalGenerator
- [ ] Create Gymnasium environment
- [ ] Add MLflow experiment tracking for new models

---

## 10. Testing Strategy

### Paper Trading Engine
- Test order validation (margin, leverage, funds)
- Test SL/TP execution on candle updates
- Test P&L calculation accuracy
- Test partial position closes
- Test liquidation scenarios

### Alert System
- Test rule matching (exact, regex, ranges)
- Test SMTP delivery (mock or local SMTP server)
- Test Telegram delivery (mock Telegram API)
- Test concurrent alert generation
- Test alert deduplication

### New Collectors
- Mock HTTP responses for all APIs
- Test parsing logic (JSON, XML, HTML)
- Test error handling (rate limits, timeouts)
- Test deduplication (same article from multiple sources)

### ML Extensions
- Test LSTM data pipeline (shape, scaling)
- Test RL environment step() mechanics
- Test regime clustering convergence
- Test integration with SignalGenerator

---

## 11. Security Considerations

1. **API Keys** : Store in environment variables, never commit to git
   - Blockchain.com API key (optional, for rate limits)
   - Etherscan API key (optional)
   - Telegram bot token (optional)
   - SMTP credentials (optional)

2. **Database Access** : All queries parameterized (SQLAlchemy ORM)

3. **Order Validation** : Strict validation before executing paper trades
   - Insufficient margin → reject order
   - Leverage > max → reject order
   - Balance < fees → reject order

4. **Alert Message Filtering** : No sensitive data in alerts
   - Don't expose user balance in email/Telegram
   - Only send abstract: "Portfolio loss > 5%"

5. **Worker Task Isolation** : Each worker process runs with limited permissions
   - No direct database writes outside transactions
   - No access to other users' accounts

---

## 12. Performance & Scalability

### Paper Trading Executor
- **Trigger** : On each new candle (every 1-5 minutes depending on timeframe)
- **Load** : ~100 paper accounts × 50 positions each = 5,000 checks per trigger
- **Optimization** : Batch candle processing; use PostgreSQL indexes on (account_id, symbol)

### Alert Evaluator
- **Trigger** : Every signal generated + periodic price check
- **Load** : ~100 rules × ~30 symbols = 3,000 rule evaluations
- **Optimization** : Cache rule conditions in memory; batch database inserts

### New Collectors
- **Frequency** : Etherscan (15 min), Blockchain.com (30 min), Regulatory (daily), News (hourly)
- **Rate Limits** : Etherscan free tier = 5 calls/sec; implement exponential backoff
- **Optimization** : Batch API calls; parallelize with asyncio

### ML Training
- **LSTM Training** : ~5 epochs × 2000 samples = 10 seconds per symbol per run (async in background)
- **Regime Clustering** : K-means fit on 10k candles ~ 100ms per symbol
- **Storage** : Models in MinIO (S3) for versioning

---

## 13. Deployment & Docker Updates

### New Docker Services
```yaml
# Option 1: Integrate into existing ml-worker
# → Add paper_trading_executor + alert_evaluator + new collectors to ml-worker

# Option 2: Separate worker for each component
alert-worker:
  build: ...
  depends_on:
    - timescaledb
    - minio
  env_file: .env
  networks:
    - backend-net

paper-trading-worker:
  build: ...
  depends_on:
    - timescaledb
  networks:
    - backend-net
```

### CI/CD Updates
- Unit tests for all new components (pytest)
- Type checking (mypy --strict)
- Code formatting (ruff)
- Docker build verification
- Integration tests with real database schema

---

## Conclusion

This architecture maintains the project's core principles while extending capabilities for:
- **Noah** : Paper trading to backtest signals + alerts for quick decisions
- **Sarah** : Regulatory alerts + new sources for journalistic coverage
- **Aleksandar** : Simplified alerts + ML enhancements for portfolio understanding

All components follow async/await patterns, Pydantic validation, and proper error handling. Implementation occurs in phases with clear boundaries and minimal cross-team dependencies.
