# 07 — Paper Trading & Alert System Specifications

> **This document is for ALL teams.** It defines the paper trading engine and alert system architecture that will integrate with existing signal generation, backtesting, and portfolio tracking.
>
> **Status**: Design Phase (Sprint 10 optional, but recommended to plan early)
> **Owner**: Backend (paper trading + alerts API), ML (signal → auto-trade logic), Frontend (UI + configuration)

---

## Executive Summary

### Problem Statement

The cadrage (project brief) explicitly requires:
1. **Paper trading**: "Passage d'ordre en paper trading pour simuler le trading" — users need a simulated trading account to test signal generation without real money.
2. **Alerts**: Three personas (Noah, Sarah, Aleksandar) demand configurable alerts on signals, news, regulatory events, and price movements.

### Current State

| Component | Status | Location |
|-----------|--------|----------|
| Signal generation | ✅ Complete | `src/ml/signal_generator.py`, `trading_signals` table |
| Signal outcome tracking | ✅ Complete | `signal_outcomes` table (post-hoc evaluation) |
| Backtesting (historical) | ✅ Complete | `src/ml/backtesting/backtest_engine.py` |
| **Paper trading** | ❌ Missing | Needs full implementation |
| **Real-time alerts** | ❌ Missing | Needs full implementation |
| Portfolio (real positions) | ✅ Partial | `src/api/routers/portfolio.py` + `portfolio` table (manual only) |

### What This Design Adds

```
Signal Generator (existing)
    ↓
    ├→ [Paper Trading Engine (NEW)]
    │    ├ Simulated account with initial balance
    │    ├ Auto-execute buy/sell on signals (confidence >= threshold)
    │    ├ SL/TP management + liquidation
    │    ├ P&L tracking (real-time + historical)
    │    └ API endpoints + Frontend UI
    │
    ├→ [Alert System (NEW)]
    │    ├ Rule engine: signal_alert, news_alert, price_alert
    │    ├ Multi-channel: email, Telegram, webhook, in-app
    │    ├ User-configurable rules per symbol/event
    │    └ APScheduler integration for background evaluation
    │
    └→ Signal Outcomes (existing)
```

---

## A. PAPER TRADING SYSTEM

### A.1 — Data Model

#### 1. PaperAccount

**Purpose**: Each user has one paper trading account with a simulated balance.

```python
# Model: src/shared/models/paper_trading.py
@dataclass(frozen=True)
class PaperAccount:
    """Simulated trading account for a user."""
    user_id: UUID
    initial_balance_usdt: Decimal  # Starting capital
    current_balance_usdt: Decimal  # Cash on hand
    total_equity_usdt: Decimal     # cash + positions_value
    realized_pnl: Decimal          # Closed trades P&L
    unrealized_pnl: Decimal        # Open positions P&L
    total_return: Decimal          # (total_equity - initial_balance) / initial_balance
    sharpe_ratio: float | None     # Annualised (computed on trade returns)
    max_drawdown: float            # Peak-to-trough %
    win_rate: float | None         # % of winning trades
    created_at: datetime
    updated_at: datetime
```

**Database table: `paper_accounts`**

```sql
CREATE TABLE paper_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    initial_balance_usdt NUMERIC(20, 2) NOT NULL,
    current_balance_usdt NUMERIC(20, 2) NOT NULL,
    total_equity_usdt NUMERIC(20, 2) NOT NULL,
    realized_pnl NUMERIC(20, 4) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(20, 4) NOT NULL DEFAULT 0,
    total_return NUMERIC(10, 6) NOT NULL DEFAULT 0,
    sharpe_ratio NUMERIC(10, 6) NULL,
    max_drawdown NUMERIC(10, 6) NULL,
    win_rate NUMERIC(10, 6) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_paper_accounts_user_id ON paper_accounts(user_id);
```

---

#### 2. PaperOrder

**Purpose**: Represents a buy/sell order placed in the simulated account.

```python
@dataclass(frozen=True)
class PaperOrder:
    """A single simulated trading order."""
    id: UUID
    user_id: UUID
    symbol: str
    side: Literal["BUY", "SELL"]  # or LONG/SHORT
    order_type: Literal["MARKET", "LIMIT"]
    quantity: Decimal              # Amount of crypto
    entry_price: Decimal           # Price at execution
    # For limit orders
    limit_price: Decimal | None
    # Timestamps
    created_at: datetime
    executed_at: datetime | None   # When filled (NULL if cancelled)
    # Links to signal + position
    signal_id: UUID | None
    paper_position_id: UUID | None # Links to open position
    # Order status
    status: Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"]
    rejection_reason: str | None   # e.g., "Insufficient balance"
```

**Database table: `paper_orders`**

```sql
CREATE TABLE paper_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(10) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    limit_price NUMERIC(20, 8) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE NULL,
    signal_id UUID NULL REFERENCES trading_signals(id) ON DELETE SET NULL,
    paper_position_id UUID NULL REFERENCES paper_positions(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL,
    rejection_reason TEXT NULL,
    CHECK (side IN ('BUY', 'SELL')),
    CHECK (order_type IN ('MARKET', 'LIMIT')),
    CHECK (status IN ('PENDING', 'FILLED', 'CANCELLED', 'REJECTED'))
);
CREATE INDEX idx_paper_orders_user ON paper_orders(user_id);
CREATE INDEX idx_paper_orders_symbol ON paper_orders(symbol);
CREATE INDEX idx_paper_orders_status ON paper_orders(status);
CREATE INDEX idx_paper_orders_signal ON paper_orders(signal_id);
```

---

#### 3. PaperPosition

**Purpose**: Represents an open long/short position in the simulated account.

```python
@dataclass(frozen=True)
class PaperPosition:
    """An open simulated trading position."""
    id: UUID
    user_id: UUID
    symbol: str
    side: Literal["LONG", "SHORT"]
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal         # Last market price
    entry_timestamp: datetime
    # Risk management
    stop_loss_price: Decimal | None
    take_profit_prices: list[Decimal]  # Multiple TP levels
    # P&L tracking
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal    # (unrealized_pnl / entry_notional) * 100
    # Position metadata
    leverage: int | None           # e.g., 1, 2, 5, 10, 20
    margin_required: Decimal | None
    # Closing
    closed_at: datetime | None
    close_price: Decimal | None
    close_reason: Literal["SL_HIT", "TP_HIT", "MANUAL", "SIGNAL_REVERSED"] | None
    realized_pnl: Decimal | None   # Computed when closed
```

**Database table: `paper_positions`**

```sql
CREATE TABLE paper_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    current_price NUMERIC(20, 8) NOT NULL,
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    stop_loss_price NUMERIC(20, 8) NULL,
    take_profit_prices JSONB NOT NULL DEFAULT '[]',
    unrealized_pnl NUMERIC(20, 4) NOT NULL DEFAULT 0,
    unrealized_pnl_pct NUMERIC(10, 6) NOT NULL DEFAULT 0,
    leverage INTEGER NULL,
    margin_required NUMERIC(20, 4) NULL,
    closed_at TIMESTAMP WITH TIME ZONE NULL,
    close_price NUMERIC(20, 8) NULL,
    close_reason VARCHAR(50) NULL,
    realized_pnl NUMERIC(20, 4) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CHECK (side IN ('LONG', 'SHORT')),
    CHECK (close_reason IS NULL OR close_reason IN ('SL_HIT', 'TP_HIT', 'MANUAL', 'SIGNAL_REVERSED'))
);
CREATE INDEX idx_paper_positions_user ON paper_positions(user_id);
CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol);
CREATE INDEX idx_paper_positions_open ON paper_positions(user_id, closed_at) WHERE closed_at IS NULL;
```

---

#### 4. PaperTrade (Journal Entry)

**Purpose**: Log of every trade execution for audit and analytics.

```python
@dataclass(frozen=True)
class PaperTrade:
    """Completed trade (from entry to exit)."""
    id: UUID
    user_id: UUID
    symbol: str
    entry_order_id: UUID
    exit_order_id: UUID | None
    entry_price: Decimal
    exit_price: Decimal | None
    quantity: Decimal
    entry_at: datetime
    exit_at: datetime | None
    realized_pnl: Decimal | None
    realized_pnl_pct: Decimal | None
    exit_reason: Literal["SL_HIT", "TP_HIT", "MANUAL", "SIGNAL_REVERSED"] | None
    duration_minutes: int | None
    # Signals/rules that triggered
    trigger_signal_id: UUID | None
    trigger_rule: str | None       # e.g., "rsi_overbought_multi_tf"
```

**Database table: `paper_trades`**

```sql
CREATE TABLE paper_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    entry_order_id UUID NOT NULL REFERENCES paper_orders(id),
    exit_order_id UUID NULL REFERENCES paper_orders(id),
    entry_price NUMERIC(20, 8) NOT NULL,
    exit_price NUMERIC(20, 8) NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    entry_at TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_at TIMESTAMP WITH TIME ZONE NULL,
    realized_pnl NUMERIC(20, 4) NULL,
    realized_pnl_pct NUMERIC(10, 6) NULL,
    exit_reason VARCHAR(50) NULL,
    duration_minutes INTEGER NULL,
    trigger_signal_id UUID NULL REFERENCES trading_signals(id),
    trigger_rule VARCHAR(100) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_paper_trades_user ON paper_trades(user_id);
CREATE INDEX idx_paper_trades_symbol ON paper_trades(symbol);
CREATE INDEX idx_paper_trades_entry_at ON paper_trades(entry_at DESC);
```

---

### A.2 — Business Logic

#### Order Execution Rules

1. **Market Orders (automatic from signals)**
   - Match latest `crypto_prices.close` for the symbol
   - Deduct trading fees (0.05% taker) immediately
   - Reject if balance < (quantity * entry_price * leverage_margin_req)
   - Fire immediately upon signal generation

2. **Limit Orders (user-placed)**
   - Remain PENDING until price touches limit
   - Check every 1h or 4h candle close
   - Convert to MARKET when limit is hit

3. **Stop-Loss & Take-Profit**
   - Evaluate on every candle close (1h timeframe minimum)
   - If price ≤ SL, auto-execute MARKET order to close position
   - If price ≥ any TP, auto-execute partial or full close
   - Log exit reason in `close_reason` field

4. **Leverage & Margin**
   - User can select leverage: 1x (spot), 2x, 5x, 10x, 20x
   - Enforce 2x margin rule: `margin_required = position_notional / leverage * 2`
   - Liquidate position if `free_margin < 0`

5. **Fee Calculation**
   - Entry: `notional * 0.0005` (taker fee)
   - Exit: `notional * 0.0005` (taker fee)
   - Funding rate: ignored in V1 (paper trading doesn't have funding)

#### Auto-Trading from Signals

**Trigger**: When `SignalGenerator.generate()` produces a signal with `confidence >= SIGNAL_CONFIDENCE_THRESHOLD` (0.6).

```python
async def auto_trade_on_signal(
    session: AsyncSession,
    signal: TradingSignal,
    current_user_id: UUID,
) -> PaperOrder | None:
    """
    Called by signal generation pipeline.

    1. Check user has paper trading enabled
    2. Check account balance
    3. Create market order with:
       - quantity = (available_balance / signal.confidence_score) × leverage
       - entry_price = current price
       - SL = signal.stop_loss (computed by signal generator)
       - TP = signal.take_profit (list)
    4. Return filled order or rejection
    """
    ...
```

Recommendation: Add signal fields (not yet in `TradingSignal`):
```python
stop_loss_price: Decimal | None
take_profit_prices: list[Decimal]
```

---

### A.3 — REST API Endpoints

#### Account Management

```
POST   /api/v1/paper-trading/account
       Body: { initial_balance_usdt: 10000.0 }
       → Create paper account for current user
       Returns: PaperAccountResponse

GET    /api/v1/paper-trading/account
       → Get account summary (balance, equity, P&L, metrics)
       Returns: PaperAccountResponse

DELETE /api/v1/paper-trading/account
       → Close account (archive trades, liquidate positions)
       Returns: { success: bool, archived_trades: int }

POST   /api/v1/paper-trading/account/reset
       → Reset account to initial balance (clear all trades/positions)
       Returns: PaperAccountResponse
```

#### Order Management

```
POST   /api/v1/paper-trading/orders
       Body: {
         symbol: "BTCUSDT",
         side: "BUY",
         quantity: 0.5,
         order_type: "MARKET" | "LIMIT",
         limit_price: 65000.0 (if LIMIT),
         take_profit_prices: [68000.0, 70000.0],
         stop_loss_price: 62000.0
       }
       → Place order (MARKET executes immediately, LIMIT pending)
       Returns: PaperOrderResponse

GET    /api/v1/paper-trading/orders
       Query: ?status=FILLED&symbol=BTCUSDT&limit=50&page=1
       → List orders with pagination + filtering
       Returns: [PaperOrderResponse], meta

GET    /api/v1/paper-trading/orders/{order_id}
       → Get order details
       Returns: PaperOrderResponse

PATCH  /api/v1/paper-trading/orders/{order_id}
       Body: { limit_price: 65000.0 } | { status: "CANCELLED" }
       → Modify pending limit order or cancel
       Returns: PaperOrderResponse

DELETE /api/v1/paper-trading/orders/{order_id}
       → Cancel order if PENDING
       Returns: { success: bool }
```

#### Position Management

```
GET    /api/v1/paper-trading/positions
       → List all open positions + closed positions (optional)
       Query: ?include_closed=false&symbol=BTCUSDT&limit=50
       Returns: [PaperPositionResponse], meta

GET    /api/v1/paper-trading/positions/{position_id}
       → Get position details (entry, current price, P&L, SL/TP)
       Returns: PaperPositionResponse

PATCH  /api/v1/paper-trading/positions/{position_id}
       Body: {
         stop_loss_price: 62000.0,
         take_profit_prices: [68000.0, 70000.0]
       }
       → Update SL/TP on open position
       Returns: PaperPositionResponse

POST   /api/v1/paper-trading/positions/{position_id}/close
       Body: { close_reason: "MANUAL" }
       → Manually close position at current market price
       Returns: PaperPositionResponse (with close_price, realized_pnl)

POST   /api/v1/paper-trading/positions/{position_id}/partial-close
       Body: { quantity_to_close: 0.25 }
       → Close part of position, keep remainder open
       Returns: [PaperPositionResponse] (old + new position)
```

#### Trade Journal & Analytics

```
GET    /api/v1/paper-trading/trades
       Query: ?symbol=BTCUSDT&start_date=2026-01-01&end_date=2026-03-14&limit=100&page=1
       → List all closed trades with P&L details
       Returns: [PaperTradeResponse], meta

GET    /api/v1/paper-trading/trades/{trade_id}
       → Get single trade details
       Returns: PaperTradeResponse

GET    /api/v1/paper-trading/analytics
       Query: ?period=30d | 90d | ytd
       → Compute metrics:
         - Daily/weekly P&L curve
         - Win rate, profit factor
         - Max drawdown, Sharpe ratio
         - Trade duration stats
         - Symbol performance breakdown
       Returns: PaperAnalyticsResponse {
         period: "30d",
         total_trades: 25,
         winning_trades: 18,
         losing_trades: 7,
         win_rate: 0.72,
         profit_factor: 2.15,
         sharpe_ratio: 1.45,
         max_drawdown: 0.12,
         total_pnl: 1250.50,
         total_return_pct: 0.125,
         by_symbol: { BTCUSDT: {...}, ETHUSDT: {...} },
         daily_pnl_curve: [{date: "2026-01-01", pnl: 50.0, equity: 10050.0}, ...]
       }

GET    /api/v1/paper-trading/account/performance-vs-signals
       → Compare paper trading P&L vs signal quality metrics
       → Link trades to signals that triggered them
       Returns: {
         signals_used: 25,
         signals_correct: 18,
         signal_win_rate: 0.72,
         paper_trading_trades: 25,
         paper_trading_win_rate: 0.72,
         correlation: 0.95
       }
```

---

### A.4 — Pydantic Schemas (API Layer)

```python
# src/api/schemas.py additions

class PaperAccountResponse(BaseModel):
    """Summary of paper trading account."""
    id: UUID
    user_id: UUID
    initial_balance_usdt: float
    current_balance_usdt: float
    total_equity_usdt: float
    realized_pnl: float
    unrealized_pnl: float
    total_return: float
    sharpe_ratio: float | None
    max_drawdown: float | None
    win_rate: float | None
    created_at: datetime
    updated_at: datetime

class PaperOrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    symbol: str
    side: str
    order_type: str
    quantity: float
    entry_price: float
    limit_price: float | None
    status: str
    rejection_reason: str | None
    signal_id: UUID | None
    created_at: datetime
    executed_at: datetime | None

class PaperPositionResponse(BaseModel):
    id: UUID
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_timestamp: datetime
    stop_loss_price: float | None
    take_profit_prices: list[float]
    leverage: int | None
    margin_required: float | None
    closed_at: datetime | None
    close_price: float | None
    realized_pnl: float | None

class PaperTradeResponse(BaseModel):
    id: UUID
    symbol: str
    entry_price: float
    exit_price: float | None
    quantity: float
    entry_at: datetime
    exit_at: datetime | None
    realized_pnl: float | None
    realized_pnl_pct: float | None
    duration_minutes: int | None
    exit_reason: str | None

class PaperAnalyticsResponse(BaseModel):
    period: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_pnl: float
    total_return_pct: float
    by_symbol: dict[str, dict]
    daily_pnl_curve: list[dict]
```

---

### A.5 — Service Layer (Business Logic)

**File**: `src/api/services/paper_trading_service.py`

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

class PaperTradingService:
    """Manage paper trading accounts, orders, positions."""

    # Account management
    async def create_account(
        self,
        db: AsyncSession,
        user_id: UUID,
        initial_balance: Decimal,
    ) -> PaperAccountOrm:
        """Create paper account for user."""
        ...

    async def get_account(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> PaperAccountOrm:
        """Get account (raise if not found)."""
        ...

    # Order management
    async def place_order(
        self,
        db: AsyncSession,
        user_id: UUID,
        symbol: str,
        side: str,  # BUY | SELL
        quantity: Decimal,
        order_type: str,  # MARKET | LIMIT
        limit_price: Decimal | None = None,
        stop_loss_price: Decimal | None = None,
        take_profit_prices: list[Decimal] | None = None,
        signal_id: UUID | None = None,
    ) -> PaperOrderOrm:
        """
        Create and execute order.
        - MARKET: execute immediately at current price
        - LIMIT: create PENDING, will execute when price hits
        """
        ...

    async def cancel_order(
        self,
        db: AsyncSession,
        user_id: UUID,
        order_id: UUID,
    ) -> PaperOrderOrm:
        """Cancel PENDING order."""
        ...

    async def get_orders(
        self,
        db: AsyncSession,
        user_id: UUID,
        symbol: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PaperOrderOrm], int]:
        """List user's orders with filtering."""
        ...

    # Position management
    async def get_open_positions(
        self,
        db: AsyncSession,
        user_id: UUID,
        symbol: str | None = None,
    ) -> list[PaperPositionOrm]:
        """List all open positions."""
        ...

    async def close_position(
        self,
        db: AsyncSession,
        user_id: UUID,
        position_id: UUID,
        close_reason: str = "MANUAL",
    ) -> tuple[PaperPositionOrm, PaperTradeOrm]:
        """Close position, create trade journal entry."""
        ...

    async def update_position_sl_tp(
        self,
        db: AsyncSession,
        user_id: UUID,
        position_id: UUID,
        stop_loss: Decimal | None = None,
        take_profit_prices: list[Decimal] | None = None,
    ) -> PaperPositionOrm:
        """Update SL/TP on open position."""
        ...

    # Analytics
    async def compute_account_metrics(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        """Compute Sharpe, max drawdown, win rate from trade history."""
        ...

    async def get_analytics(
        self,
        db: AsyncSession,
        user_id: UUID,
        period_days: int = 30,
    ) -> dict:
        """Compute detailed analytics: daily P&L, by-symbol breakdown, etc."""
        ...

# Background job (APScheduler)
async def job_process_pending_orders_and_sl_tp() -> None:
    """
    Runs every 1h: check all pending limit orders and open positions
    for SL/TP hits. Process fills and closures.
    """
    ...
```

---

### A.6 — Frontend Integration

**Location**: `src/frontend/pages/5_paper_trading.py` (new page)

```
Dashboard:
├─ Account Summary Card
│  ├ Initial Balance | Current Balance | Total Equity
│  ├ Realized P&L | Unrealized P&L | Total Return %
│  └ Metrics: Sharpe | Max DD | Win Rate
│
├─ Active Positions Table
│  ├ Symbol | Side | Qty | Entry | Current | P&L | P&L % | SL | TP | Actions
│  └ Actions: Modify SL/TP | Close | Partial Close
│
├─ Recent Trades Table
│  ├ Entry Date | Symbol | Side | Qty | Entry | Exit | Duration | P&L | Exit Reason
│  └ Filter by symbol, date range
│
├─ Orders Panel
│  ├ Place New Order (Market / Limit)
│  ├ Pending Orders
│  └ Order History
│
├─ Analytics Charts
│  ├ Daily P&L Curve (Plotly area chart)
│  ├ Cumulative Returns
│  ├ Drawdown Waterfall
│  ├ Win Rate by Symbol (bar chart)
│  ├ P&L Distribution (histogram)
│  └ Trade Duration Distribution
│
└─ Account Controls
   ├ Reset Account Button
   ├ Download Trade Journal (CSV)
   └ Link to signal history (for correlation analysis)
```

---

## B. ALERT SYSTEM

### B.1 — Data Model

#### 1. AlertRule

**Purpose**: User-defined condition to trigger notifications.

```python
@dataclass(frozen=True)
class AlertRule:
    """A user-defined alert rule."""
    id: UUID
    user_id: UUID
    rule_name: str
    rule_type: Literal["SIGNAL", "NEWS", "PRICE", "REGULATORY"]

    # Condition
    condition: dict  # Dynamic based on rule_type
    # Examples:
    # SIGNAL: { "symbol": "BTCUSDT", "signal_type": "BUY", "min_confidence": 0.7 }
    # NEWS: { "keyword": "SEC", "sentiment_threshold": -0.5 }
    # PRICE: { "symbol": "BTCUSDT", "trigger": "ABOVE", "price": 70000 }
    # REGULATORY: { "agencies": ["SEC", "ESMA"], "keywords": ["stablecoin"] }

    # Notification channels (at least one)
    notify_email: bool
    notify_telegram: bool
    notify_webhook: bool
    notify_in_app: bool

    webhook_url: str | None       # e.g., https://n8n.user.com/webhook/crypto-alerts
    telegram_chat_id: str | None  # Private chat ID

    # Status
    enabled: bool
    cooldown_minutes: int         # Don't re-fire if already fired in last N minutes
    last_fired_at: datetime | None

    created_at: datetime
    updated_at: datetime
```

**Database table: `alert_rules`**

```sql
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(20) NOT NULL,
    condition JSONB NOT NULL,
    notify_email BOOLEAN NOT NULL DEFAULT TRUE,
    notify_telegram BOOLEAN NOT NULL DEFAULT FALSE,
    notify_webhook BOOLEAN NOT NULL DEFAULT FALSE,
    notify_in_app BOOLEAN NOT NULL DEFAULT TRUE,
    webhook_url VARCHAR(1000) NULL,
    telegram_chat_id VARCHAR(50) NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    cooldown_minutes INTEGER NOT NULL DEFAULT 30,
    last_fired_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CHECK (rule_type IN ('SIGNAL', 'NEWS', 'PRICE', 'REGULATORY')),
    CHECK (
        notify_email OR notify_telegram OR notify_webhook OR notify_in_app
    )
);
CREATE INDEX idx_alert_rules_user ON alert_rules(user_id, enabled);
CREATE INDEX idx_alert_rules_last_fired ON alert_rules(last_fired_at);
```

---

#### 2. AlertHistory

**Purpose**: Log of every alert fired (for audit, deduplication, and replay prevention).

```python
@dataclass(frozen=True)
class AlertHistory:
    """Record of a fired alert."""
    id: UUID
    user_id: UUID
    rule_id: UUID
    rule_type: str
    symbol: str | None
    trigger_value: dict | str      # Context: { "signal_type": "BUY", "confidence": 0.85 }

    # Delivery status
    sent_email: bool
    sent_telegram: bool
    sent_webhook: bool
    sent_in_app: bool

    email_error: str | None
    telegram_error: str | None
    webhook_error: str | None

    fired_at: datetime
```

**Database table: `alert_history`**

```sql
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    rule_type VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NULL,
    trigger_value JSONB NOT NULL,
    sent_email BOOLEAN NOT NULL DEFAULT FALSE,
    sent_telegram BOOLEAN NOT NULL DEFAULT FALSE,
    sent_webhook BOOLEAN NOT NULL DEFAULT FALSE,
    sent_in_app BOOLEAN NOT NULL DEFAULT FALSE,
    email_error TEXT NULL,
    telegram_error TEXT NULL,
    webhook_error TEXT NULL,
    fired_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_alert_history_user_fired ON alert_history(user_id, fired_at DESC);
CREATE INDEX idx_alert_history_rule ON alert_history(rule_id);
```

---

#### 3. InAppAlert

**Purpose**: Transient in-app notifications shown in Streamlit UI.

```python
@dataclass(frozen=True)
class InAppAlert:
    """In-app notification (shown in Streamlit sidebar/toast)."""
    id: UUID
    user_id: UUID
    message: str
    alert_type: Literal["INFO", "WARNING", "ERROR", "SUCCESS"]
    rule_id: UUID | None
    read: bool
    created_at: datetime
    expires_at: datetime  # Auto-dismiss after 24h
```

**Database table: `in_app_alerts`**

```sql
CREATE TABLE in_app_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    alert_type VARCHAR(20) NOT NULL,
    rule_id UUID NULL REFERENCES alert_rules(id) ON DELETE SET NULL,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    CHECK (alert_type IN ('INFO', 'WARNING', 'ERROR', 'SUCCESS'))
);
CREATE INDEX idx_in_app_alerts_user_read ON in_app_alerts(user_id, read);
```

---

### B.2 — Alert Types & Trigger Logic

#### Type 1: Signal Alert

**When**: New signal generated with matching criteria.

```
Trigger:
  if signal.symbol in user_watched_symbols
  AND signal.signal_type matches rule.condition["signal_type"]
  AND signal.confidence_score >= rule.condition["min_confidence"]
  → FIRE ALERT

Message:
  "🔔 SIGNAL: {symbol} {signal_type} confidence={confidence:.2f}"
  "Entry: ${entry_price} | SL: ${sl} | TP: ${tp1}, ${tp2}"
  "{rules_triggered}"

Broadcast: Email, Telegram, Webhook, In-App
```

Example rule config:
```json
{
  "rule_type": "SIGNAL",
  "condition": {
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "signal_type": "BUY",
    "min_confidence": 0.75
  },
  "cooldown_minutes": 60
}
```

---

#### Type 2: News Alert

**When**: New news article published matching keywords + sentiment.

```
Trigger:
  if article.symbol in user_watched_symbols
  AND any keyword in rule.condition["keywords"] appears in title/content
  AND article.sentiment_score <= rule.condition["sentiment_threshold"]
  → FIRE ALERT

Message:
  "📰 NEWS: {headline}"
  "Symbol: {symbol} | Sentiment: {sentiment_score:.2f} | Source: {source}"
  "{source_url}"

Broadcast: Email, Telegram, Webhook, In-App
```

Example rule config:
```json
{
  "rule_type": "NEWS",
  "condition": {
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "keywords": ["SEC", "regulation", "enforcement"],
    "sentiment_threshold": -0.5
  },
  "cooldown_minutes": 120
}
```

---

#### Type 3: Price Alert

**When**: Spot price crosses configured thresholds.

```
Trigger (evaluated on every 1h candle close):
  if side == "ABOVE" and close > price_threshold → FIRE
  if side == "BELOW" and close < price_threshold → FIRE

Message:
  "📊 PRICE: {symbol} crossed {side} ${threshold}"
  "Current price: ${current_price}"

Broadcast: Telegram (instant), Email (batch), In-App
```

Example rule config:
```json
{
  "rule_type": "PRICE",
  "condition": {
    "symbol": "BTCUSDT",
    "trigger": "ABOVE",
    "price": 70000.0
  },
  "cooldown_minutes": 0
}
```

---

#### Type 4: Regulatory Alert

**When**: SEC, ESMA, or other authority publishes guidance/rules affecting crypto.

```
Trigger:
  if regulatory document/announcement mentions crypto
  AND keywords in rule.condition["keywords"] match
  → FIRE ALERT

Message:
  "⚖️ REGULATORY: {agency} publishes guidance on {topic}"
  "{content_summary}"
  "{source_url}"

Broadcast: Email, In-App
```

Example rule config:
```json
{
  "rule_type": "REGULATORY",
  "condition": {
    "agencies": ["SEC", "ESMA"],
    "keywords": ["stablecoin", "custody", "leverage"]
  },
  "cooldown_minutes": 240
}
```

---

### B.3 — Delivery Channels

#### Email (SMTP)

**Provider**: Free SMTP (Gmail, Mailgun, or self-hosted).

```python
# src/api/services/alert_service.py
async def send_email_alert(
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> bool:
    """Send via SMTP (async wrapper around aiosmtplib or similar)."""
    ...
```

Configuration (`.env`):
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=cryptobot@example.com
SMTP_PASSWORD=xxxx
SMTP_FROM_EMAIL=alerts@cryptobot.com
```

---

#### Telegram Bot

**Setup**: User creates bot token and provides chat ID.

```python
async def send_telegram_alert(
    chat_id: str,
    message: str,
) -> bool:
    """Send via Telegram Bot API."""
    ...
```

User flows:
1. User creates Telegram bot via BotFather → receives token
2. Stores token in `.env` as `TELEGRAM_BOT_TOKEN`
3. Users add bot to their private chat → copy chat ID
4. Input chat ID in alert rule creation

---

#### Webhook (n8n / Zapier)

**Setup**: User provides webhook URL for external integration.

```python
async def send_webhook_alert(
    webhook_url: str,
    payload: dict,
) -> bool:
    """POST JSON to user's webhook."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
    return resp.status_code == 200
```

Payload format:
```json
{
  "alert_id": "uuid",
  "timestamp": "2026-03-14T15:30:00Z",
  "rule_type": "SIGNAL",
  "symbol": "BTCUSDT",
  "trigger_value": {
    "signal_type": "BUY",
    "confidence": 0.85
  },
  "message": "🔔 SIGNAL: BTCUSDT BUY confidence=0.85"
}
```

---

#### In-App (Streamlit)

**Display**: Toast + sidebar notification area in Streamlit.

```python
# src/frontend/components/alert_toast.py
import streamlit as st

def show_alert(message: str, alert_type: str = "info"):
    """Display in-app alert (maps to in_app_alerts table)."""
    if alert_type == "success":
        st.success(message, icon="✅")
    elif alert_type == "warning":
        st.warning(message, icon="⚠️")
    elif alert_type == "error":
        st.error(message, icon="❌")
    else:
        st.info(message, icon="ℹ️")
```

---

### B.4 — REST API Endpoints

#### Rule Management

```
POST   /api/v1/alerts/rules
       Body: {
         rule_name: "BTC BUY Signals",
         rule_type: "SIGNAL",
         condition: {
           symbols: ["BTCUSDT"],
           signal_type: "BUY",
           min_confidence: 0.75
         },
         notify_email: true,
         notify_telegram: true,
         notify_webhook: false,
         notify_in_app: true,
         cooldown_minutes: 60
       }
       → Create alert rule
       Returns: AlertRuleResponse

GET    /api/v1/alerts/rules
       Query: ?enabled=true&rule_type=SIGNAL&limit=50
       → List user's alert rules
       Returns: [AlertRuleResponse], meta

GET    /api/v1/alerts/rules/{rule_id}
       → Get rule details
       Returns: AlertRuleResponse

PUT    /api/v1/alerts/rules/{rule_id}
       Body: { rule_name, condition, notify_*, cooldown_minutes, enabled }
       → Update rule
       Returns: AlertRuleResponse

DELETE /api/v1/alerts/rules/{rule_id}
       → Delete rule
       Returns: { success: bool }

PATCH  /api/v1/alerts/rules/{rule_id}/toggle
       → Toggle enabled/disabled
       Returns: AlertRuleResponse
```

#### Alert History

```
GET    /api/v1/alerts/history
       Query: ?rule_id=uuid&rule_type=SIGNAL&start_date=2026-01-01&limit=100&page=1
       → List alerts fired for current user
       Returns: [AlertHistoryResponse], meta

GET    /api/v1/alerts/history/{alert_id}
       → Get details of a fired alert + delivery status
       Returns: AlertHistoryResponse
```

#### In-App Alerts

```
GET    /api/v1/alerts/in-app
       Query: ?unread=true&limit=20
       → Get unread in-app alerts for sidebar
       Returns: [InAppAlertResponse]

PATCH  /api/v1/alerts/in-app/{alert_id}/read
       → Mark as read
       Returns: InAppAlertResponse

DELETE /api/v1/alerts/in-app/{alert_id}
       → Dismiss alert
       Returns: { success: bool }

PATCH  /api/v1/alerts/in-app/read-all
       → Mark all as read
       Returns: { marked_read: int }
```

#### Configuration

```
POST   /api/v1/alerts/channels/telegram/verify
       Body: { chat_id: "123456" }
       → Send test message to verify chat ID
       Returns: { success: bool, message: "Test sent" }

POST   /api/v1/alerts/channels/email/verify
       Body: { email: "user@example.com" }
       → Send verification email
       Returns: { success: bool, message: "Check email" }

PATCH  /api/v1/alerts/channels/webhook
       Body: { webhook_url: "https://..." }
       → Update webhook URL
       Returns: { webhook_url: "..." }
```

---

### B.5 — Background Job (APScheduler)

**Location**: `src/etl/jobs.py`

```python
async def job_evaluate_alert_rules() -> None:
    """
    Runs every 1h: evaluate all enabled alert rules.

    1. For SIGNAL alerts: check trading_signals table for new signals
    2. For NEWS alerts: check news_articles for recent articles
    3. For PRICE alerts: check latest crypto_prices against thresholds
    4. For REGULATORY alerts: check regulatory_docs (new table in Phase 2)

    5. For each matching rule:
       - Check cooldown: has it fired in the last N minutes?
       - If not, send notifications on all enabled channels
       - Log to alert_history
       - Create in-app alert
       - Update last_fired_at
    """
    from src.api.services.alert_service import AlertService
    from src.shared.database import async_session_factory

    service = AlertService()
    async with async_session_factory() as session:
        await service.evaluate_all_rules(session)
```

---

### B.6 — Pydantic Schemas (API Layer)

```python
# src/api/schemas.py additions

class AlertRuleResponse(BaseModel):
    id: UUID
    user_id: UUID
    rule_name: str
    rule_type: str
    condition: dict
    notify_email: bool
    notify_telegram: bool
    notify_webhook: bool
    notify_in_app: bool
    webhook_url: str | None
    telegram_chat_id: str | None
    enabled: bool
    cooldown_minutes: int
    last_fired_at: datetime | None
    created_at: datetime
    updated_at: datetime

class AlertRuleCreateRequest(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=255)
    rule_type: str = Field(..., regex="^(SIGNAL|NEWS|PRICE|REGULATORY)$")
    condition: dict
    notify_email: bool = True
    notify_telegram: bool = False
    notify_webhook: bool = False
    notify_in_app: bool = True
    webhook_url: str | None = None
    telegram_chat_id: str | None = None
    cooldown_minutes: int = Field(30, ge=0, le=1440)

class AlertHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    rule_id: UUID
    rule_type: str
    symbol: str | None
    trigger_value: dict
    sent_email: bool
    sent_telegram: bool
    sent_webhook: bool
    sent_in_app: bool
    email_error: str | None
    telegram_error: str | None
    webhook_error: str | None
    fired_at: datetime

class InAppAlertResponse(BaseModel):
    id: UUID
    message: str
    alert_type: str
    rule_id: UUID | None
    read: bool
    created_at: datetime
    expires_at: datetime
```

---

### B.7 — Service Layer

**File**: `src/api/services/alert_service.py`

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

class AlertService:
    """Manage alert rules, evaluate triggers, deliver notifications."""

    # Rule CRUD
    async def create_rule(
        self,
        db: AsyncSession,
        user_id: UUID,
        rule_name: str,
        rule_type: str,
        condition: dict,
        notify_email: bool,
        notify_telegram: bool,
        notify_webhook: bool,
        notify_in_app: bool,
        webhook_url: str | None = None,
        telegram_chat_id: str | None = None,
        cooldown_minutes: int = 30,
    ) -> AlertRuleOrm:
        """Create new alert rule."""
        ...

    async def get_rules(
        self,
        db: AsyncSession,
        user_id: UUID,
        rule_type: str | None = None,
        enabled: bool | None = None,
    ) -> list[AlertRuleOrm]:
        """List user's rules with filtering."""
        ...

    async def update_rule(
        self,
        db: AsyncSession,
        user_id: UUID,
        rule_id: UUID,
        **kwargs,
    ) -> AlertRuleOrm:
        """Update rule fields."""
        ...

    async def delete_rule(
        self,
        db: AsyncSession,
        user_id: UUID,
        rule_id: UUID,
    ) -> bool:
        """Delete rule."""
        ...

    # Evaluation + Delivery
    async def evaluate_all_rules(
        self,
        db: AsyncSession,
    ) -> dict[str, int]:
        """
        Run evaluation for all enabled rules.
        Returns: { rule_type: count_fired }
        """
        ...

    async def _evaluate_signal_alerts(
        self,
        db: AsyncSession,
    ) -> int:
        """Check for new signals matching user rules."""
        ...

    async def _evaluate_news_alerts(
        self,
        db: AsyncSession,
    ) -> int:
        """Check for news articles matching keywords."""
        ...

    async def _evaluate_price_alerts(
        self,
        db: AsyncSession,
    ) -> int:
        """Check latest prices against thresholds."""
        ...

    async def _fire_alert(
        self,
        db: AsyncSession,
        rule: AlertRuleOrm,
        trigger_value: dict,
        symbol: str | None = None,
    ) -> None:
        """
        Send alert via enabled channels and log to history.
        Checks cooldown before firing.
        """
        ...

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> tuple[bool, str | None]:
        """Send email alert. Returns (success, error_msg)."""
        ...

    async def send_telegram(
        self,
        chat_id: str,
        message: str,
    ) -> tuple[bool, str | None]:
        """Send Telegram alert."""
        ...

    async def send_webhook(
        self,
        webhook_url: str,
        payload: dict,
    ) -> tuple[bool, str | None]:
        """Send webhook POST."""
        ...

    async def create_in_app_alert(
        self,
        db: AsyncSession,
        user_id: UUID,
        message: str,
        alert_type: str,
        rule_id: UUID | None = None,
    ) -> InAppAlertOrm:
        """Create transient in-app alert."""
        ...
```

---

### B.8 — Frontend Integration

**Location**: `src/frontend/pages/2_alerts.py` (new page) + sidebar notification area

```
Dashboard:
├─ Alert Configuration Panel
│  ├ Create New Rule Button
│  │  ├ Type selector (SIGNAL | NEWS | PRICE | REGULATORY)
│  │  ├ Dynamic condition builder
│  │  ├ Channel toggles + inputs (email, telegram, webhook)
│  │  └ Cooldown slider
│  │
│  └─ Existing Rules Table
│     ├ Rule Name | Type | Enabled | Last Fired | Actions
│     ├ Actions: Edit | Test | Disable | Delete
│     └ Inline condition display
│
├─ Alert History
│  ├ Timeline of fired alerts (reverse chronological)
│  ├ Filters: rule_type, symbol, date range
│  └ Delivery status: ✅ sent | ❌ failed
│
├─ In-App Notification Sidebar
│  ├ Unread count badge
│  ├ Recent alerts (expandable list)
│  ├ Auto-dismiss after 24h
│  └ Mark as read / Dismiss buttons
│
└─ Channel Configuration
   ├ Email: verified (user email from profile)
   ├ Telegram: bot token + chat ID inputs + verify button
   ├ Webhook: URL input + test button
   └ Send test alert button
```

---

## C. INTEGRATION ARCHITECTURE

### C.1 — Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Signal Generation (4h)                   │
│  ML Engine → Rule Engine → SignalGenerator.generate()           │
│  (confidence >= 0.6 threshold)                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
        ┌─────────────────┐   ┌──────────────────┐
        │  Paper Trading  │   │  Alert System    │
        │  (AUTO-TRADE)   │   │  (FIRE ALERTS)   │
        │                 │   │                  │
        │ 1. Check balance│   │ 1. Signal rule   │
        │ 2. Place order  │   │    matches?      │
        │ 3. Create pos   │   │ 2. Check cooldown│
        │ 4. Track P&L    │   │ 3. Send notif    │
        │ 5. Journal      │   │ 4. Log history   │
        └─────────────────┘   └──────────────────┘
              ↓                        ↓
        ┌─────────────┐         ┌─────────────┐
        │ BDD: orders │         │ BDD: alerts │
        │ positions   │         │ in_app      │
        │ trades      │         │ history     │
        └─────────────┘         └─────────────┘

Other triggers:

News Article Published (hourly scrape)
  ↓
News Alert Rule Evaluation
  ├ Sentiment score OK?
  ├ Keywords match?
  └ Notify users

Price Crosses Threshold (hourly candle close)
  ↓
Price Alert Rule Evaluation
  ├ Price >= threshold OR price <= threshold?
  └ Notify users

Regulatory Announcement (daily check)
  ↓
Regulatory Alert Rule Evaluation
  ├ Agency + keywords match?
  └ Notify users
```

---

### C.2 — Database Diagram (Summary)

```
Users
├─ PaperAccount (1-1)
│   ├─ PaperOrder (1-M)
│   │   └─ PaperPosition (1-M, via position_id)
│   │       ├─ PaperTrade (1-M, when closed)
│   │       └─ TradingSignal (N-M, linked by signal_id)
│   │
│   ├─ AlertRule (1-M)
│   │   └─ AlertHistory (1-M)
│   │       └─ InAppAlert (1-M, when notify_in_app=true)
│   │
│   └─ InAppAlert (1-M, direct)
│
Trading Signals (from ML engine)
├─ PaperOrder (when triggers auto-trade)
├─ AlertHistory (when rule matches)
└─ SignalOutcome (post-hoc evaluation)

News Articles
└─ AlertHistory (when matches rule)
```

---

### C.3 — Sequence Diagram: Signal → Paper Trade → Alert

```
Signal Generator (4h candle)
  │
  ├→ Generate TradingSignal (conf=0.85, BUY, SL, TP)
  │   └→ Save to trading_signals table
  │
  ├→ PAPER TRADING PIPELINE:
  │   └→ auto_trade_on_signal(signal, user_id)
  │       ├ Get paper_accounts[user_id]
  │       ├ Check balance ≥ required margin
  │       ├ Create PaperOrder (MARKET, BUY, qty=..., entry_price=current_price)
  │       │ └→ Save to paper_orders (status=FILLED)
  │       ├ Create PaperPosition (LONG, entry_price, SL, TP)
  │       │ └→ Save to paper_positions (open)
  │       ├ Update paper_accounts balance & unrealized_pnl
  │       └→ Log to journal (optional)
  │
  └→ ALERT PIPELINE (async, every 1h via APScheduler):
      └→ evaluate_signal_alerts()
          ├ Find all AlertRule with rule_type=SIGNAL
          ├ For each rule:
          │   ├ symbol in condition["symbols"]?
          │   ├ signal_type == condition["signal_type"]?
          │   ├ confidence >= condition["min_confidence"]?
          │   ├ Last fired > cooldown_minutes ago?
          │   └ IF ALL YES:
          │       ├ send_email_alert(...)
          │       ├ send_telegram_alert(...)
          │       ├ send_webhook_alert(...)
          │       ├ create_in_app_alert(...)
          │       ├ Log to alert_history
          │       └ Update rule.last_fired_at
```

---

### C.4 — Configuration & Dependencies

#### Django-like Settings (`.env` additions)

```bash
# Paper Trading
PAPER_TRADING_ENABLED=true
PAPER_TRADING_INITIAL_BALANCE_USDT=10000.0
PAPER_TRADING_AUTO_TRADE_ENABLED=true
PAPER_TRADING_MIN_CONFIDENCE_TO_AUTO_TRADE=0.6

# Alerts
ALERTS_ENABLED=true

# Email alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=cryptobot@example.com
SMTP_PASSWORD=xxxx
SMTP_FROM_EMAIL=alerts@cryptobot.com

# Telegram alerts
TELEGRAM_BOT_TOKEN=xxxx:xxxx
TELEGRAM_API_URL=https://api.telegram.org

# Alert evaluation schedule (APScheduler)
ALERT_EVAL_SCHEDULE_CRON="0 * * * *"  # Every hour
PAPER_TRADING_EVAL_SCHEDULE_CRON="0 * * * *"  # Every hour for SL/TP
```

#### Requirements.txt additions

```
aiosmtplib >= 2.0.0          # Async SMTP
python-telegram-bot >= 20.0  # Telegram Bot API
httpx >= 0.25.0              # Async HTTP client
```

---

### C.5 — Personas' Use Cases

#### Noah (Trader)

```
1. Creates paper account with $10,000 initial balance
2. Defines alert rules:
   - "BTC BUY Signals": rule_type=SIGNAL, symbol=BTCUSDT, signal_type=BUY, min_confidence=0.75
   - "BTC Price Alert": rule_type=PRICE, symbol=BTCUSDT, trigger=ABOVE, price=70000
3. Enables auto-trading: signals with confidence >= 0.8 auto-execute
4. Monitors dashboard:
   - Open positions + live P&L
   - Closed trades journal
   - Performance metrics (Sharpe, max DD, win rate)
5. Receives alerts on:
   - Every BUY signal fired (email + Telegram)
   - Price crosses $70k (in-app toast + Telegram)
6. Manually closes positions or adjusts SL/TP as needed
7. Downloads trade journal for analysis
```

#### Sarah (Journalist)

```
1. Creates alert rules:
   - "Regulatory News": rule_type=NEWS, keywords=["SEC", "regulation"], sentiment_threshold=-0.7
   - "ESMA Announcements": rule_type=REGULATORY, agencies=["ESMA"]
2. Sets notification:
   - In-app (Streamlit notification sidebar)
   - Email (daily digest)
3. Uses dashboard to:
   - View recent alerts in timeline
   - Filter by keyword, date, agency
   - Access full article + sentiment score
4. No paper trading (not relevant to her role)
```

#### Aleksandar (Investor)

```
1. Creates paper account (for learning)
2. Defines alert rules:
   - "Altcoin Opportunities": rule_type=SIGNAL, symbols=[many alts], min_confidence=0.7
   - "Major Crypto Moves": rule_type=PRICE, trigger=ABOVE, price=*various*
3. Sets notification:
   - Telegram (instant mobile alerts)
   - Webhook → n8n → custom workflow (optional)
4. Uses paper trading to:
   - Test signal-following strategy
   - Backtest portfolio performance
   - Compare different alert configurations
5. Views analytics:
   - Which signals were most profitable?
   - Best symbols by win rate?
   - Correlation: signal quality vs actual returns
```

---

## D. IMPLEMENTATION ROADMAP

### Phase 1: Paper Trading (Sprint 10, Weeks 1-2)

| Week | Task | Owner | Status |
|------|------|-------|--------|
| 1 | Create DB schema (4 new tables) | Backend | - |
| 1 | Pydantic models (PaperAccount, Order, Position, Trade) | Backend | - |
| 1 | Service layer: account, order, position CRUD | Backend | - |
| 1 | API endpoints: /paper-trading/* | Backend | - |
| 2 | Auto-trading integration from signal generator | ML + Backend | - |
| 2 | SL/TP evaluation job (APScheduler) | Backend + DevOps | - |
| 2 | Analytics computation (Sharpe, max DD, win rate) | Backend | - |
| 2 | Frontend: Paper Trading page + charts | Frontend | - |

### Phase 2: Alert System (Sprint 10, Weeks 3-4)

| Week | Task | Owner | Status |
|------|------|--------|--------|
| 3 | Create DB schema (3 new tables) | Backend | - |
| 3 | Pydantic models (AlertRule, History, InAppAlert) | Backend | - |
| 3 | Service layer: rule CRUD + delivery methods | Backend | - |
| 3 | Email integration (SMTP async) | Backend | - |
| 3 | Telegram bot integration | Backend | - |
| 4 | Webhook integration | Backend | - |
| 4 | APScheduler job: evaluate_all_rules() | ETL + Backend | - |
| 4 | API endpoints: /alerts/* | Backend | - |
| 4 | Frontend: Alerts config page + sidebar notifications | Frontend | - |
| 4 | Testing + documentation | All | - |

### Phase 3: Advanced Features (Optional, Post-Sprint 10)

- RL environment using paper trading for simulated trades
- Portfolio optimization algorithms (mean-variance, Sharpe maximization)
- Advanced analytics dashboard (correlation heatmaps, regime detection)
- Backtesting v2: replay historical signals against paper trading engine
- Multi-user alert aggregation (team accounts)

---

## E. TESTING STRATEGY

### Unit Tests

```
✅ PaperAccountService.create_account() → creates account, validates balance
✅ PaperOrderService.place_order() → validates balance, creates order, rejects if insufficient
✅ PaperPositionService.evaluate_sl_tp() → detects SL/TP hits, closes position correctly
✅ AlertService.evaluate_signal_alerts() → matches rules, respects cooldown
✅ AlertService.send_email() → correct subject/body format
✅ AlertService.send_telegram() → correct JSON payload
```

### Integration Tests

```
✅ Signal generation → auto-trade → position created → correct P&L
✅ Close position → trade journal entry created
✅ New alert rule → next evaluation fires alert → history logged
✅ Multiple rules, one cooldown expires → re-fire correctly
✅ Email + Telegram simultaneously → both sent (or fail independently)
```

### E2E Tests

```
✅ User flow: register → create paper account → receive signal → auto-trade → check position P&L → close trade → download journal
✅ User flow: register → create alert rule → trigger condition → receive email + telegram + in-app notification
```

---

## F. MIGRATION STRATEGY

### Alembic Migration: Paper Trading Tables

**File**: `src/etl/migrations/versions/20260314_add_paper_trading_tables.py`

```python
def upgrade():
    # Create paper_accounts, paper_orders, paper_positions, paper_trades
    # Create indexes
    # Create foreign keys
    pass

def downgrade():
    drop_table("paper_trades")
    drop_table("paper_positions")
    drop_table("paper_orders")
    drop_table("paper_accounts")
```

### Alembic Migration: Alert Tables

**File**: `src/etl/migrations/versions/20260314_add_alert_tables.py`

```python
def upgrade():
    # Create alert_rules, alert_history, in_app_alerts
    # Create indexes
    pass

def downgrade():
    drop_table("in_app_alerts")
    drop_table("alert_history")
    drop_table("alert_rules")
```

---

## G. SECURITY & COMPLIANCE

### Paper Trading

- **Simulation only**: No real funds at risk
- **Account isolation**: Each user's paper account separate (user_id FK)
- **Audit trail**: All orders + positions logged for compliance review

### Alerts

- **Email**: Use authenticated SMTP (TLS/SSL)
- **Telegram**: Bot token stored in `.env`, never exposed
- **Webhook**: User provides URL (validate it's HTTPS in production)
- **Rate limiting**: Prevent alert spam (cooldown enforced)
- **Privacy**: Alert history scoped to user (no cross-user leaks)

---

## H. SUCCESS CRITERIA

### Paper Trading (Sprint 10)

- [ ] Paper account created successfully with initial balance
- [ ] Auto-trading from signals works (orders executed, positions tracked)
- [ ] SL/TP logic works (positions close correctly)
- [ ] P&L metrics computed accurately (Sharpe, win rate, max DD)
- [ ] Frontend dashboard displays all data clearly
- [ ] Trade journal exportable (CSV)
- [ ] 80%+ unit + integration test coverage

### Alerts (Sprint 10)

- [ ] Alert rules created/updated/deleted via API
- [ ] Signal alerts fire when rules match
- [ ] Email delivery works (test with real SMTP)
- [ ] Telegram delivery works (test with bot token)
- [ ] Webhook integration works (test with n8n/Zapier)
- [ ] Cooldown respected (no duplicate fires)
- [ ] In-app alerts display in Streamlit sidebar
- [ ] Alert history queryable (pagination + filtering)
- [ ] 80%+ unit + integration test coverage

### Integration

- [ ] Signal → Paper Trade → Alert flow works end-to-end
- [ ] Personas can use both systems intuitively
- [ ] No data loss on service restart (all persisted)
- [ ] Performance acceptable (alert eval < 10s for 100 rules)

---

## I. GLOSSARY

| Term | Definition |
|------|------------|
| **Paper Trading** | Simulated trading with virtual balance (no real funds) |
| **Paper Account** | User's simulated trading account (1 per user) |
| **Paper Order** | Simulated buy/sell order (MARKET or LIMIT) |
| **Paper Position** | Open long/short position in paper account |
| **Paper Trade** | Closed position with realized P&L (journal entry) |
| **Alert Rule** | User-defined condition (e.g., "BTC BUY signals") |
| **Alert History** | Log of fired alerts + delivery status |
| **Cooldown** | Minimum time between firing same rule twice |
| **SL (Stop Loss)** | Price at which position auto-closes (loss limit) |
| **TP (Take Profit)** | Price at which position auto-closes (profit target) |
| **Leverage** | Multiplier on position size (1x, 2x, 5x, ..., 20x) |
| **Margin Safety** | Required free margin = 2x position notional |
| **Unrealized P&L** | Profit/loss on open position (marked to market) |
| **Realized P&L** | Profit/loss on closed position (locked in) |
| **Sharpe Ratio** | Risk-adjusted return metric (annualized) |
| **Max Drawdown** | Largest peak-to-trough portfolio decline |
| **Win Rate** | Fraction of trades with positive return |

---

## J. APPENDIX: Example Alert Configurations

### Example 1: Noah's Multi-Timeframe Signal Alert

```json
{
  "rule_name": "Multi-TF BTC Convergence",
  "rule_type": "SIGNAL",
  "condition": {
    "symbol": "BTCUSDT",
    "signal_type": "BUY",
    "min_confidence": 0.8,
    "required_rules": ["rsi_overbought_multi_tf", "bollinger_squeeze"]
  },
  "notify_email": true,
  "notify_telegram": true,
  "notify_webhook": false,
  "notify_in_app": true,
  "telegram_chat_id": "123456789",
  "cooldown_minutes": 120
}
```

### Example 2: Sarah's Regulatory Alert

```json
{
  "rule_name": "SEC Stablecoin Guidance",
  "rule_type": "REGULATORY",
  "condition": {
    "agencies": ["SEC"],
    "keywords": ["stablecoin", "custody", "issuer"]
  },
  "notify_email": true,
  "notify_telegram": false,
  "notify_webhook": false,
  "notify_in_app": true,
  "cooldown_minutes": 480
}
```

### Example 3: Aleksandar's Price + Webhook Alert

```json
{
  "rule_name": "Altcoin Pump Alert",
  "rule_type": "PRICE",
  "condition": {
    "symbols": ["SOLUSDT", "ADAUSDT", "XRPUSDT"],
    "trigger": "ABOVE",
    "price": 150.0
  },
  "notify_email": false,
  "notify_telegram": true,
  "notify_webhook": true,
  "notify_in_app": true,
  "webhook_url": "https://n8n.aleksandar.com/webhook/crypto-price-alerts",
  "telegram_chat_id": "987654321",
  "cooldown_minutes": 60
}
```

---

**End of Document**

---

## NEXT STEPS

1. **Backend Team**: Create DB migrations + ORM models + service layer
2. **API Team**: Implement REST endpoints + error handling
3. **Frontend Team**: Build UI pages + Streamlit components
4. **ML Team**: Integrate auto-trading trigger into SignalGenerator
5. **DevOps Team**: Configure APScheduler jobs + SMTP / Telegram in Docker
6. **QA**: Write comprehensive tests + run integration suite
7. **All Teams**: Participate in cross-team E2E testing

Estimated effort: 4-6 weeks for full implementation + testing.
