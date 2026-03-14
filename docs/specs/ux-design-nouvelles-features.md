# Frontend UX Design — New Features for CryptoBot

**Project:** CryptoBot | **Stack:** Streamlit + Plotly, Dark Theme
**Date:** 2026-03-14 | **Audience:** Frontend Engineer (Aleksandar, Sarah, Noah)

---

## Table of Contents

1. [Design System & Existing Patterns](#design-system--existing-patterns)
2. [Feature 1: Paper Trading (Live/Backtest Account)](#feature-1-paper-trading)
3. [Feature 2: Alerts & Notifications](#feature-2-alerts--notifications)
4. [Feature 3: Clustering Visualization & Regime Detection](#feature-3-clustering-visualization--regime-detection)
5. [Feature 4: On-Chain Metrics](#feature-4-on-chain-metrics)
6. [Feature 5: Regulatory Sources in Veille](#feature-5-regulatory-sources-in-veille)
7. [User Flows & Personas](#user-flows--personas)
8. [i18n (FR/EN Labels)](#i18n-fren-labels)
9. [Implementation Checklist](#implementation-checklist)

---

## Design System & Existing Patterns

### Current Design Language

- **Theme:** Dark mode primary (light mode supported via CSS custom properties)
- **Color Palette:**
  - Accent: `#22d3ee` (cyan-400) primary, `#0ea5e9` (sky-500) secondary
  - Success: `#3fb950`, Warning: `#d29922`, Error: `#f85149`
  - Surface: `#161b22`, Background: `#0d1117`
- **Components:** st.metric, st.tabs, st.container(border=True), st.form, st.plotly_chart
- **Typography:** Sidebar headers gradient, metric labels UPPERCASE, body sans-serif
- **Icons:** Lucide icons via CDN (e.g., `icon-trending-up`, `icon-bell`)

### Existing Layout Patterns

1. **Page Header + Status Indicator** (Dashboard)
2. **Selector + Refresh Layout** (Symbol, Timeframe, button)
3. **Two-Column (Content + Sidebar)** (Dashboard: chart + news, Veille: news + sentiment)
4. **Tabbed Interface** (Portfolio: tabs for portfolio/watchlist/chatbot)
5. **Bordered Containers with Subheaders** (all pages)
6. **Metric Cards in Rows** (KPI displays with delta)
7. **Form Submit + Validation** (Portfolio add/edit)
8. **DataFrames with computed columns** (Portfolio, signal history)

### Styling Conventions

- Use `st.container(border=True)` for card grouping
- Use `st.metric()` for KPIs with optional delta
- Use `st.columns([a, b, c])` for responsive layouts
- Use `st.form()` for multi-field input with validation outside the form block
- Use `st.plotly_chart(fig, use_container_width=True)` for charts
- Use `st.cache_data(ttl=N)` for API response caching with appropriate TTLs
- Markdown with unsafe_allow_html for custom styling only when needed

---

## Feature 1: Paper Trading

### Overview

**Personas:** Noah (Trader), Aleksandar (Investor)
**Purpose:** Simulate trading without real capital; track P&L, build trading journal, backtest signal strategies.

### Requirements

- **Account Summary Card:** Simulated balance, total P&L (USD + %), open P&L, closed P&L
- **Open Positions Table:** Symbol | Direction (LONG/SHORT) | Entry | Current | Qty | P&L% | SL | TP | Close Position
- **Order Form:** Symbol | Direction | Quantity | Entry Price (or "current") | Stop Loss | Take Profit x3 | Leverage | Memo
- **Closed Trades Journal:** Date | Symbol | Direction | Entry | Exit | P&L% | Holding Time | Outcome
- **Equity Curve Chart:** Cumulative balance over time (daily)
- **Drawdown Analysis:** Max drawdown, rolling 7d/30d drawdown
- **Statistics:** Win rate, avg win/loss, Sharpe ratio, Calmar ratio

### Architecture Decision

**WHERE TO ADD:** New page **`6_paper_trading.py`** with main tab: **Paper Account**.
**RATIONALE:** Paper trading is a complete feature (not just a section) deserving its own page in the multi-page nav. Keeps Portfolio page focused on real holdings. Matches Noah's need for dedicated trade journal + Aleksandar's backtesting interest.

---

### Wireframe: Paper Trading Page

```
╔════════════════════════════════════════════════════════════════════════════╗
║ 📊 Paper Trading Journal                                  [Sync to Portfolio?] ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────────────────────────┬───────────────────────────────┐   ║
║  │ 💰 Account Balance: $10,000          │ 📈 Total P&L: +2,345 (+23.5%) │   ║
║  │ 💵 Invested: $7,230 | Available: $2 │ 📊 Realized: +1,200 | Unreal: +1 ║
║  │                                      │                               │   ║
║  └─────────────────────────────────────┴───────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📊 [Equity Curve]      [Drawdown Analysis]    [Statistics] (tabs)    │   ║
║  │                                                                      │   ║
║  │  Equity Curve (daily):                                             │   ║
║  │  ┌──────────────────────────────────────────────────────────────┐  │   ║
║  │  │                                    __. ________                │  │   ║
║  │  │                      ______........'                          │  │   ║
║  │  │         ___________.'   .....                                │  │   ║
║  │  │     _.'               .                                      │  │   ║
║  │  │ _.'                                                          │  │   ║
║  │  │_|__________________________________________________________|  │   ║
║  │  │ 7d  | 30d | 90d | YTD | ALL | [Realized P&L only toggle]    │  │   ║
║  │  └──────────────────────────────────────────────────────────────┘  │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 🔓 Open Positions (3)                      [+ New Trade]  [Close All] │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │ Symbol │ Dir │ Entry  │ Current │ Qty  │ P&L%   │ SL     │ TP      │   ║
║  ├────────┼─────┼────────┼─────────┼──────┼────────┼────────┼─────────┤   ║
║  │ BTC    │ LNG │$42,100 │ $43,250 │ 0.2  │ +2.72% │$40,100 │$45,000 │   ║
║  │ ETH    │ LNG │$2,300  │ $2,180  │ 5.0  │ -5.22% │$2,100  │$2,600  │   ║
║  │ SOL    │ SHT │$125.00 │ $128.50 │ 20.0 │ -2.80% │$130.00 │$120.00 │   ║
║  │        │ [Close] [Edit]                                             │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ ➕ Place New Trade                                                    │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │ Symbol: [BTC        ▼] | Direction: [LONG▼] | Quantity: [0.5    ] │   ║
║  │ Entry Price: [Current] | Stop Loss: [$40,100    ] | SL %: [-5.0%] │   ║
║  │ Take Profit #1: [$45,000  ] | TP #2: [$46,000] | TP #3: [$48,000] │   ║
║  │ Leverage: [1x    ▼] (max 3x on top 13) | Memo: [optional note...] │   ║
║  │                                                                      │   ║
║  │ [Validate inputs] [📋 Place Trade] [🔄 Reset]                      │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📖 Closed Trades Journal (12 total)                                  │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │ Date    │ Sym │ Dir │ Entry  │ Exit   │ P&L%   │ Hold Time │ Outcome │   ║
║  ├─────────┼─────┼─────┼────────┼────────┼────────┼───────────┼─────────┤   ║
║  │ 2026-03 │ BTC │ LNG │$42,000 │$44,500 │ +5.95% │ 12h 35m   │ ✅ Win  │   ║
║  │ 2026-02 │ ETH │ SHT │$2,350  │$2,200  │ +6.40% │ 5d 3h     │ ✅ Win  │   ║
║  │ 2026-02 │ SOL │ LNG │$125.00 │$120.50 │ -3.60% │ 2h 15m    │ ❌ Loss │   ║
║  │ [CSV Export Button] [Filter by Symbol]                              │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

### Key Components & Streamlit Patterns

#### 1. Account Summary Metrics (Top)

```python
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Balance", "$10,000.00", delta="$0.00 (no positions closed yet)")
with col2:
    st.metric("Total P&L", "+23.5%", delta="$2,345", delta_color="normal")
with col3:
    st.metric("Open P&L", "+12.3%", delta="Unrealized on 3 positions")
with col4:
    st.metric("Max Drawdown", "-8.2%", delta="From peak $10,850")
```

#### 2. Equity Curve Tab

```python
with st.tabs(["Equity Curve", "Drawdown", "Statistics"]):
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_dates, y=equity_values,
            mode='lines', name='Account Balance',
            fill='tozeroy'
        ))
        st.plotly_chart(fig, use_container_width=True)

        # Radio selector for date range
        period = st.radio("Period", ["7d", "30d", "90d", "YTD", "ALL"],
                          horizontal=True)
```

#### 3. Open Positions Table

```python
positions_df = pd.DataFrame([
    {
        "Symbol": "BTC",
        "Direction": "LONG",
        "Entry": "$42,100",
        "Current": "$43,250",
        "Qty": "0.2",
        "P&L %": "+2.72%",
        "SL": "$40,100",
        "TP": "$45,000 / $46,000",
    },
    # ... more rows
])

st.dataframe(positions_df, use_container_width=True, hide_index=True)

# Per-row action buttons
for idx, row in positions_df.iterrows():
    col_sym, col_close, col_edit = st.columns([2, 1, 1])
    with col_sym:
        st.write(row["Symbol"])
    with col_close:
        if st.button("Close", key=f"close_{idx}"):
            # Close the position
            pass
```

#### 4. Order Form (st.form)

```python
with st.form("place_order_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.selectbox("Symbol", frontend_settings.tracked_symbols)
    with col2:
        direction = st.selectbox("Direction", ["LONG", "SHORT"])
    with col3:
        quantity = st.number_input("Quantity", min_value=0.0, step=0.001)

    col_entry, col_sl = st.columns(2)
    with col_entry:
        entry_type = st.radio("Entry", ["Current price", "Custom"],
                              horizontal=True)
        if entry_type == "Custom":
            entry_price = st.number_input("Entry Price", min_value=0.0)
    with col_sl:
        sl_price = st.number_input("Stop Loss ($)", min_value=0.0)
        sl_pct = st.number_input("or SL (%)", min_value=-50.0, max_value=0.0)

    # Take Profit levels (x3)
    tp_col1, tp_col2, tp_col3 = st.columns(3)
    with tp_col1:
        tp1 = st.number_input("TP #1 ($)", min_value=0.0)
    with tp_col2:
        tp2 = st.number_input("TP #2 ($)", min_value=0.0)
    with tp_col3:
        tp3 = st.number_input("TP #3 ($)", min_value=0.0)

    leverage = st.selectbox("Leverage (2x margin limit)", ["1x", "2x", "3x"])
    memo = st.text_input("Trade memo (optional)", placeholder="e.g., 'RSI 4h div'")

    submitted = st.form_submit_button("Place Trade", type="primary")

if submitted:
    # Validate & submit
    pass
```

#### 5. Closed Trades Journal

```python
trades_df = pd.DataFrame([
    {
        "Date": "2026-03-14",
        "Symbol": "BTC",
        "Direction": "LONG",
        "Entry": "$42,000",
        "Exit": "$44,500",
        "P&L %": "+5.95%",
        "Hold Time": "12h 35m",
        "Outcome": "✅ Win",
    },
])

st.dataframe(trades_df, use_container_width=True, hide_index=True)

# CSV export
csv_data = trades_df.to_csv(index=False).encode('utf-8')
st.download_button("Export trades as CSV", csv_data, "trades.csv", "text/csv")
```

---

### Data Model (API Contract)

**GET `/api/v1/paper-trading/account`**
```json
{
  "balance": 10000.0,
  "invested": 7230.0,
  "available": 2770.0,
  "total_pnl": 2345.0,
  "total_pnl_pct": 0.2345,
  "realized_pnl": 1200.0,
  "unrealized_pnl": 1145.0,
  "max_drawdown": -0.082,
  "created_at": "2025-01-01T00:00:00Z"
}
```

**GET `/api/v1/paper-trading/positions?status=open`**
```json
{
  "data": [
    {
      "id": "pos_123",
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "entry_price": 42100.0,
      "current_price": 43250.0,
      "quantity": 0.2,
      "leverage": 1,
      "stop_loss": 40100.0,
      "take_profits": [45000.0, 46000.0, 48000.0],
      "opened_at": "2026-03-10T12:30:00Z",
      "pnl": 230.0,
      "pnl_pct": 0.0272
    }
  ]
}
```

**POST `/api/v1/paper-trading/positions`**
```json
{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "quantity": 0.2,
  "entry_price": null,
  "stop_loss": 40100.0,
  "take_profits": [45000.0, 46000.0, 48000.0],
  "leverage": 1,
  "memo": "RSI 4h divergence"
}
```

**GET `/api/v1/paper-trading/equity-curve?period=30d`**
```json
{
  "data": [
    {"date": "2026-02-13T00:00:00Z", "balance": 9850.0},
    {"date": "2026-02-14T00:00:00Z", "balance": 9920.0},
    ...
  ]
}
```

---

## Feature 2: Alerts & Notifications

### Overview

**Personas:** Noah (Trader), Sarah (Journalist)
**Purpose:** Rule-based alerts: emit notifications when market conditions change (price, indicator, regime, regulatory news).

### Requirements

- **Alert Rules Page:** Create/manage rules with conditions (symbol, indicator, operator, threshold, notification channel)
- **Condition Builder:** Symbol | Indicator (RSI, Bollinger, Price, Regime) | Operator (>, <, ==, crossed) | Value | Channel (Email, Telegram, In-app)
- **Alert History:** Timestamp | Symbol | Condition | Triggered Value | Channel | Status (read/unread)
- **Mute/Dismiss:** Snooze alerts for 1h/4h/1d; bulk clear history
- **Smart Routing:** Notify only when confidence >= threshold (Sarah wants regulatory alerts with summary, Noah wants signal alerts with price levels)

### Architecture Decision

**WHERE TO ADD:** New page **`7_alerts.py`** OR Sidebar section in app.py with modal + badge.
**RATIONALE:** Alerts are a cross-cutting concern (not tied to a single page). A dedicated page makes sense for managing rules + history. However, *in-app notifications* should appear as a **sidebar badge + toast** wherever the user is. Start with dedicated page + in-app toast on Dashboard.

---

### Wireframe: Alerts Page

```
╔════════════════════════════════════════════════════════════════════════════╗
║ 🔔 Alerts & Notifications                          [Unread: 3] [Clear All] ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  [📋 Alert Rules] [📜 History] [⚙️ Preferences]  (tabs)                     ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📋 ALERT RULES                                           [+ New Rule] │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │ ✅ Rule 1: BTC RSI(4h) > 70 [OVERBOUGHT] → Email + In-app           │   ║
║  │    Last triggered: 2 days ago | Triggers: 12 times/month            │   ║
║  │    [Edit] [Disable] [Delete] [Test trigger]                         │   ║
║  │                                                                      │   ║
║  │ ✅ Rule 2: ETH below $2,000 [SUPPORT BREAK] → Email                 │   ║
║  │    Last triggered: 5 days ago | Triggers: 3 times/month             │   ║
║  │    [Edit] [Disable] [Delete] [Test trigger]                         │   ║
║  │                                                                      │   ║
║  │ ❌ Rule 3: SOL Regime = BEAR (disabled) → Telegram                   │   ║
║  │    Last triggered: Never | Triggers: 0 times/month                  │   ║
║  │    [Edit] [Enable] [Delete] [Test trigger]                          │   ║
║  │                                                                      │   ║
║  │ ✅ Rule 4: ESMA news alert → Email + SMS                            │   ║
║  │    Last triggered: 1 day ago | Triggers: 8 times/month              │   ║
║  │    [Edit] [Disable] [Delete]                                        │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ ➕ CREATE NEW ALERT RULE                                             │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │  Step 1: Select Trigger Type                                        │   ║
║  │  ◉ Price Alert  ○ Indicator Alert  ○ Regime Change  ○ Regulatory   │   ║
║  │                                                                      │   ║
║  │  Step 2: Configure Condition                                        │   ║
║  │  Symbol: [BTC      ▼] | Indicator: [Price ▼] | Operator: [> ▼]    │   ║
║  │  Value: [$45,000      ] | Frequency: [Once per day ▼]              │   ║
║  │                                                                      │   ║
║  │  Step 3: Select Notifications                                       │   ║
║  │  ☑ In-app toast  ☑ Email  ☐ Telegram  ☐ SMS                         │   ║
║  │                                                                      │   ║
║  │  [Validate] [Create Rule] [Cancel]                                  │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📜 ALERT HISTORY (15 alerts in last 7 days)                         │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │ [🟡 Unread] [✓ Read] [All] [Clear read]                             │   ║
║  │                                                                      │   ║
║  │ 🟡 14:32  BTC RSI > 70 (overbought) on 4h      [Mark read] [❌]      │   ║
║  │    → Current RSI: 72.3 | Entry: $43,250                             │   ║
║  │                                                                      │   ║
║  │ ✓  12:15  ETH fell below $2,100 support        [Mark unread] [❌]   │   ║
║  │    → Current: $2,085 | Rule triggered 1/10 today                   │   ║
║  │                                                                      │   ║
║  │ 🟡 10:42  🚨 ESMA warning: Leverage reporting...  [Read article] [❌] │   ║
║  │    → Regulatory | Priority: HIGH                                   │   ║
║  │                                                                      │   ║
║  │ [📥 Older alerts...]                                                │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

### Key Components & Streamlit Patterns

#### 1. Rule Creation Wizard (Multi-step form)

```python
# Step 1: Trigger type selector
trigger_type = st.radio("Trigger Type",
    ["Price", "Indicator", "Regime Change", "Regulatory"],
    horizontal=True)

# Step 2: Configure condition (conditional rendering based on trigger_type)
if trigger_type == "Price":
    symbol = st.selectbox("Symbol", frontend_settings.tracked_symbols)
    operator = st.selectbox("Operator", [">", "<", "==", "between"])
    value = st.number_input("Price threshold ($)")

elif trigger_type == "Indicator":
    symbol = st.selectbox("Symbol", frontend_settings.tracked_symbols)
    indicator = st.selectbox("Indicator",
        ["RSI", "Bollinger Bands", "MACD", "Moving Average"])
    operator = st.selectbox("Operator", [">", "<", "crossed above", "crossed below"])
    if indicator == "RSI":
        value = st.slider("RSI level", 0, 100, 70)
    elif indicator == "Bollinger Bands":
        value = st.selectbox("Position", ["touches upper", "touches lower", "squeeze"])

elif trigger_type == "Regime Change":
    symbol = st.selectbox("Symbol", frontend_settings.tracked_symbols)
    timeframe = st.selectbox("Timeframe", ["1d", "4h"])
    regime = st.selectbox("Regime type", ["Bull", "Bear", "Sideways", "Any change"])

elif trigger_type == "Regulatory":
    country = st.selectbox("Jurisdiction", ["ESMA", "SEC", "EU", "Global"])
    keywords = st.multiselect("Keywords",
        ["Leverage", "Staking", "DeFi", "Reporting", "Any"])

# Step 3: Notification channels
channels = st.multiselect("Notify via:",
    ["In-app", "Email", "Telegram", "SMS"],
    default=["In-app"])

# Submit
if st.button("Create Rule"):
    # POST to /api/v1/alerts/rules
    pass
```

#### 2. Alert History with Filtering

```python
# Filter tabs
tab_all, tab_unread, tab_price, tab_indicator = st.tabs(
    ["All", "Unread", "Price Alerts", "Indicator Alerts"])

with tab_unread:
    alerts_df = pd.DataFrame([
        {
            "Time": "14:32",
            "Symbol": "BTC",
            "Condition": "RSI > 70 (overbought)",
            "Triggered Value": "72.3",
            "Channel": "In-app, Email",
            "Read": "🟡 Unread",
        },
    ])
    st.dataframe(alerts_df, use_container_width=True, hide_index=True)

    # Bulk actions
    if st.button("Mark all as read"):
        # POST to /api/v1/alerts/mark-read
        pass
```

#### 3. Sidebar Badge + Toast (in Dashboard or all pages)

```python
# In the main app.py or a shared component
unread_alerts = client.fetch_unread_alerts_count()
if unread_alerts > 0:
    st.sidebar.warning(f"🔔 {unread_alerts} unread alerts", icon=":material/notifications:")
    if st.session_state.get("show_alert_toast"):
        latest_alert = client.fetch_latest_alert()
        st.toast(f"🔔 {latest_alert['symbol']}: {latest_alert['condition']}", icon="⚠️")
```

---

### Data Model (API Contract)

**POST `/api/v1/alerts/rules`**
```json
{
  "name": "BTC RSI overbought",
  "trigger_type": "indicator",
  "symbol": "BTCUSDT",
  "condition": {
    "indicator": "RSI",
    "timeframe": "4h",
    "operator": ">",
    "value": 70
  },
  "frequency": "once_per_day",
  "channels": ["in_app", "email"],
  "enabled": true
}
```

**GET `/api/v1/alerts/rules`**
```json
{
  "data": [
    {
      "id": "rule_123",
      "name": "BTC RSI overbought",
      "trigger_type": "indicator",
      "condition": {...},
      "enabled": true,
      "triggers_this_month": 12,
      "last_triggered_at": "2026-03-12T14:32:00Z"
    }
  ]
}
```

**GET `/api/v1/alerts/history?limit=50&unread=true`**
```json
{
  "data": [
    {
      "id": "alert_abc",
      "rule_id": "rule_123",
      "symbol": "BTCUSDT",
      "condition": "RSI > 70",
      "triggered_value": 72.3,
      "triggered_at": "2026-03-14T14:32:00Z",
      "channels": ["in_app", "email"],
      "read": false
    }
  ]
}
```

---

## Feature 3: Clustering Visualization & Regime Detection

### Overview

**Personas:** Noah (Trader), Aleksandar (Investor)
**Purpose:** Visualize market structure: clusters of correlated cryptos, current regime (bull/bear/sideways), regime timeline.

### Requirements

- **Cluster Map (Scatter Plot):** BTC/ETH/SOL/ADA/DOGE... as points, colored by cluster, sized by market cap, labeled with symbol
- **Cluster Insights:** % of market in each cluster, correlation heatmap within cluster
- **Regime Indicator (Big Visual):** Current regime badge (Bull/Bear/Sideways), gauge showing strength (0-100), timeline showing regime changes (weekly)
- **Regime Rationale:** Which indicators support this regime? (e.g., "Bull: BTC above 200d MA, ETH 4h RSI > 50")
- **Historical Regimes:** List of regime changes (date, symbol, old→new regime, trigger)

### Architecture Decision

**WHERE TO ADD:** Extend **`4_analytics.py`** (Analytics page) with new tabs:
1. Current tab: **"Market Heatmap"** (existing: KPIs, heatmap, gainers/losers, correlation, Fear & Greed)
2. New tab: **"Clustering"** (cluster map + insights)
3. New tab: **"Regime"** (regime gauge + timeline + explanation)

**RATIONALE:** Analytics is the home for market-level analysis. Regime detection feeds signal generation & portfolio risk. Keeps all "market structure" visuals together. Could also live in Dashboard as secondary section, but Analytics is cleaner.

---

### Wireframe: Regime Analysis (Analytics Tab)

```
╔════════════════════════════════════════════════════════════════════════════╗
║ 📊 Analytics                                                                ║
║  [Heatmap] [Clustering] [Regime] [Correlation] [Fear & Greed]             ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📈 MARKET REGIME — Last 30 days                                      │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │  ┌────────────────────────────────────────────────────────────────┐ │   ║
║  │  │           BULL MARKET (Strong)                              │ │   ║
║  │  │                                                             │ │   ║
║  │  │  ╔═══════════════════════════════════════════════════════╗  │ │   ║
║  │  │  ║                                                      ║  │ │   ║
║  │  │  ║    ███████████████████████████ (Strength: 78%)  ║  │ │   ║
║  │  │  ║                                                      ║  │ │   ║
║  │  │  ╚═══════════════════════════════════════════════════════╝  │ │   ║
║  │  │                                                             │ │   ║
║  │  │  Indicators Supporting Regime:                              │ │   ║
║  │  │  ✅ BTC above 200d MA (43,500 > 40,200)                     │ │   ║
║  │  │  ✅ 20/30 assets in uptrend                                 │ │   ║
║  │  │  ✅ RSI(4h) > 50 across 65% of tracked coins               │ │   ║
║  │  │  ✅ Bollinger Band walking upper (ETH, SOL, ADA)           │ │   ║
║  │  │  ⚠️  Fear & Greed = 72 (Greed territory — watch for pop)   │ │   ║
║  │  │                                                             │ │   ║
║  │  └────────────────────────────────────────────────────────────┘ │   ║
║  │                                                                      │   ║
║  │  Risk: Medium (Bull cycle mature; watch for resistance at $45k)     │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📊 Regime Timeline (1y)                                              │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │ ┌────────────────────────────────────────────────────────────────┐  │   ║
║  │ │                                                                │  │   ║
║  │ │   BEAR (Feb)       SIDEWAYS (Mar 1-10)  ▶ BULL (now)         │  │   ║
║  │ │   ════════════════════════════════════════███████            │  │   ║
║  │ │   ↓ Feb 28         ↓ Mar 1              ↓ Mar 10             │  │   ║
║  │ │   (BTC -28%)       (Vol ↓)              (BTC +12%)           │  │   ║
║  │ │                                                                │  │   ║
║  │ └────────────────────────────────────────────────────────────────┘  │   ║
║  │                                                                      │   ║
║  │ Regime Changes (30d):                                               │   ║
║  │ • 2026-03-10 12:00 UTC  SIDEWAYS → BULL  [Trigger: BTC broke above]│   ║
║  │ • 2026-03-01 08:15 UTC  BEAR → SIDEWAYS  [Trigger: Volatility drop]│   ║
║  │ • 2026-02-15 16:45 UTC  BULL → BEAR      [Trigger: FOMC news]       │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 🗺️ CLUSTER MAP (Market Segmentation)                                │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │  ┌────────────────────────────────────────────────────────────────┐ │   ║
║  │  │                                                              │ │   ║
║  │  │           Cluster A (12 assets)                           │ │   ║
║  │  │        🟢 BTC●────────●ETH 🟢                           │ │   ║
║  │  │             \       /                                    │ │   ║
║  │  │              \  ◉ /     ← Center of gravity             │ │   ║
║  │  │         AVAX●\   /●SOL                                  │ │   ║
║  │  │                \ /                                       │ │   ║
║  │  │              ADA●                                        │ │   ║
║  │  │                                                           │ │   ║
║  │  │           Cluster B (8 assets)  [Lower correlation]      │ │   ║
║  │  │              ●XRP  ●DOGE 🔴                              │ │   ║
║  │  │                    ●TRX                                   │ │   ║
║  │  │                                                           │ │   ║
║  │  │         Legend: ● Size = Market Cap                      │ │   ║
║  │  │                 🟢 Green = Uptrend | 🔴 Red = Downtrend │ │   ║
║  │  │                 ━━━ Line thickness = Correlation         │ │   ║
║  │  │                                                              │ │   ║
║  │  └────────────────────────────────────────────────────────────────┘ │   ║
║  │                                                                      │   ║
║  │  Cluster Metrics:                                                   │   ║
║  │  • Cluster A: 12 assets, avg corr = 0.68, weighted vol = 18%      │   ║
║  │  • Cluster B: 8 assets, avg corr = 0.41, weighted vol = 24%       │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

### Key Components & Streamlit Patterns

#### 1. Regime Gauge + Indicator Summary

```python
# Fetch regime data
regime = client.fetch_current_regime()  # {"regime": "BULL", "strength": 78, "indicators": [...]}

# Display regime badge + gauge
col_badge, col_gauge = st.columns([1, 2])

with col_badge:
    if regime["regime"] == "BULL":
        st.markdown("### 🟢 BULL MARKET")
        color = "#3fb950"
    elif regime["regime"] == "BEAR":
        st.markdown("### 🔴 BEAR MARKET")
        color = "#f85149"
    else:
        st.markdown("### 🟡 SIDEWAYS")
        color = "#d29922"

with col_gauge:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=regime["strength"],
        title="Regime Strength",
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 33], "color": "rgba(240, 84, 84, 0.1)"},
                {"range": [33, 66], "color": "rgba(210, 153, 34, 0.1)"},
                {"range": [66, 100], "color": "rgba(63, 185, 80, 0.1)"},
            ]
        }
    ))
    st.plotly_chart(fig, use_container_width=True)

# Supporting indicators
st.subheader("Supporting Indicators")
for indicator in regime["indicators"]:
    status = "✅" if indicator["supports"] else "⚠️"
    st.markdown(f"{status} {indicator['name']}: {indicator['value']}")
```

#### 2. Cluster Scatter Plot

```python
@st.cache_data(ttl=300)
def _fetch_cluster_data():
    return client.fetch_clustering()  # Returns symbol, x, y, cluster, market_cap, trend

cluster_data = _fetch_cluster_data()

# Build scatter plot
fig = go.Figure()

# Add points per cluster with different colors
clusters = cluster_data["clusters"]
colors = ["#22d3ee", "#0ea5e9", "#a78bfa", "#fb7185", "#fbbf24"]

for idx, cluster_id in enumerate(clusters):
    cluster_points = [d for d in cluster_data["points"] if d["cluster"] == cluster_id]

    fig.add_trace(go.Scatter(
        x=[p["x"] for p in cluster_points],
        y=[p["y"] for p in cluster_points],
        mode='markers+text',
        text=[p["symbol"] for p in cluster_points],
        textposition="top center",
        marker=dict(
            size=[p["market_cap"] / 1e9 for p in cluster_points],  # Size by market cap
            color=colors[idx % len(colors)],
            opacity=0.7,
            line=dict(width=2, color="white"),
        ),
        name=f"Cluster {idx + 1}",
        hovertemplate="<b>%{text}</b><br>Correlation: %{customdata[0]:.2f}<extra></extra>",
        customdata=[[p.get("avg_corr", 0)] for p in cluster_points],
    ))

fig.update_layout(
    title="Market Clustering (Correlation-based segmentation)",
    xaxis_title="Dimension 1 (PCA)",
    yaxis_title="Dimension 2 (PCA)",
    hovermode='closest',
    height=500,
    **_DARK_LAYOUT
)

st.plotly_chart(fig, use_container_width=True)

# Cluster metrics table
cluster_metrics = pd.DataFrame([
    {
        "Cluster": f"A ({len([p for p in cluster_data['points'] if p['cluster'] == i])} assets)",
        "Avg Correlation": f"{cluster_data['cluster_stats'][i]['avg_corr']:.2f}",
        "Volatility": f"{cluster_data['cluster_stats'][i]['volatility']:.1f}%",
    }
    for i in range(len(clusters))
])
st.dataframe(cluster_metrics, use_container_width=True, hide_index=True)
```

#### 3. Regime Timeline

```python
regime_history = client.fetch_regime_history(limit=30)

# Format timeline data
timeline_data = []
for change in regime_history:
    timeline_data.append({
        "Date": change["date"],
        "From Regime": change["from_regime"],
        "To Regime": change["to_regime"],
        "Trigger": change["trigger"],
    })

st.dataframe(pd.DataFrame(timeline_data), use_container_width=True, hide_index=True)
```

---

### Data Model (API Contract)

**GET `/api/v1/analytics/regime`**
```json
{
  "current_regime": "BULL",
  "strength": 78,
  "indicators": [
    {
      "name": "BTC above 200d MA",
      "value": "43,500 > 40,200",
      "supports": true,
      "weight": 0.3
    },
    {
      "name": "RSI(4h) > 50 (65% of assets)",
      "value": "65%",
      "supports": true,
      "weight": 0.2
    }
  ],
  "risk_level": "medium",
  "risk_note": "Bull cycle mature; watch for resistance"
}
```

**GET `/api/v1/analytics/clustering`**
```json
{
  "points": [
    {
      "symbol": "BTC",
      "x": 0.5,
      "y": 0.6,
      "cluster": 0,
      "market_cap": 950000000000,
      "trend": "UP",
      "avg_corr": 0.68
    }
  ],
  "clusters": [0, 1, 2],
  "cluster_stats": {
    "0": {
      "assets": 12,
      "avg_corr": 0.68,
      "volatility": 18.2
    }
  }
}
```

**GET `/api/v1/analytics/regime-history?days=30`**
```json
{
  "data": [
    {
      "date": "2026-03-10T12:00:00Z",
      "from_regime": "SIDEWAYS",
      "to_regime": "BULL",
      "trigger": "BTC broke above 200d MA",
      "confidence": 0.87
    }
  ]
}
```

---

## Feature 4: On-Chain Metrics

### Overview

**Personas:** Noah (Trader), Aleksandar (Investor)
**Purpose:** Display blockchain-level metrics: BTC hashrate, active addresses, gas fees, whale transactions, exchange inflows/outflows.

### Requirements

- **On-Chain KPI Cards:** BTC hashrate (EH/s), active addresses (BTC/ETH), gas fees (gwei), whale transactions (last 24h), exchange netflow
- **Time Series Charts:** Hashrate (7d/30d), active addresses (7d/30d), gas fees (hourly), whale activity (5-10 largest tx)
- **Integration:** Link on-chain data to signal generation (e.g., "High whale activity = potential dump")
- **Data Source:** Glassnode API (free tier) or Blockchain.com (free)

### Architecture Decision

**WHERE TO ADD:** New section in **`1_dashboard.py`** OR new tab in **`4_analytics.py`**.
**RATIONALE:** On-chain data is valuable for signal confirmation. Could live in:
- **Dashboard** (Noah wants integrated view: price + news + signals + on-chain)
- **Analytics** (market-level data, but on-chain is more specific to individual assets)

**CHOOSE:** Add a **section below the candlestick chart on Dashboard** with collapsible on-chain cards. This keeps Noah's integrated workflow intact. Optionally, add a **secondary Analytics tab "On-Chain"** for deep-dives.

---

### Wireframe: On-Chain Section (Dashboard)

```
╔════════════════════════════════════════════════════════════════════════════╗
║ 📊 Dashboard                                                                ║
║                                                                              ║
║  Symbol: [BTC ▼] | Timeframe: [4h ▼]                      [Refresh]        ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐   ║
║  │                                                                     │   ║
║  │                   [Candlestick Chart + Indicators]                 │   ║
║  │                                                                     │   ║
║  └─────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ⛓️ ON-CHAIN METRICS FOR BTC [Toggle] [7d | 30d]                           ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ ⚙️ Hashrate      │ 👥 Active Addresses  │ 💰 Reserve    │ 🐋 Whale    │   ║
║  │ 426 EH/s         │ 1.23M                │ 2,134,452 BTC │ Activity    │   ║
║  │ ↑ +2.3% (7d)     │ ↓ -1.2% (7d)         │ ↑ +0.8% (7d)  │ ↑↑ 8 whale  │   ║
║  │                  │                      │               │ tx / 24h    │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📈 BTC Hashrate (7d)                                                │   ║
║  │                                                                      │   ║
║  │  ┌──────────────────────────────────────────────────────────────┐   │   ║
║  │  │                                        ___╱╲╱╲____            │   ║
║  │  │                    ╱╲___________╱╲___╱╲╱╲╱╲╱╲                │   ║
║  │  │          ________╱╲╱╲╱╲╱╲╱╲╱╲╱╲                            │   ║
║  │  │     ____╱╲╱╲╱╲                                              │   ║
║  │  │ ___╱╲╱╲╱╲╱╲                                                │   ║
║  │  │_│_____________________________________________________|    │   ║
║  │  │ Mon  | Tue  | Wed | Thu | Fri | Sat | Sun              │   ║
║  │  └──────────────────────────────────────────────────────────────┘   │   ║
║  │                                                                      │   ║
║  │  [Glassnode link] [Alert when < 400 EH/s]                           │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 💰 ETH Gas Fees (Gwei) — Latest 24h                                 │   ║
║  │                                                                      │   ║
║  │  ┌─ Safe   ☑ Standard   ☐ Fast                                     │   ║
║  │  │                                                                 │   ║
║  │  │  Safe: 42 Gwei  │ Standard: 58 Gwei  │ Fast: 75 Gwei          │   ║
║  │  │  ↓ -8% (24h)    │ ↑ +5% (24h)        │ ↓ -2% (24h)            │   ║
║  │  │                                                                 │   ║
║  │  └─────────────────────────────────────────────────────────────────│   ║
║  │                                                                      │   ║
║  │  [Chart toggle] [Alert when > 100 Gwei]                             │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 🐋 Top Whale Transactions (BTC, last 48h)                           │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │ Time      │ Amount     │ From          │ To            │ Status    │   ║
║  ├───────────┼────────────┼───────────────┼───────────────┼───────────┤   ║
║  │ 2h ago    │ 2,500 BTC  │ Gemini wallet │ Unknown       │ Pending   │   ║
║  │           │ ($108M)    │               │               │ 🚨 alert  │   ║
║  │ 14h ago   │ 1,245 BTC  │ Kraken        │ Trezor addr   │ Confirmed │   ║
║  │ 1d ago    │ 3,421 BTC  │ Exchange hot  │ Genesis block │ Old       │   ║
║  │                                                                      │   ║
║  │ [Show more] [Download CSV]                                          │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

### Key Components & Streamlit Patterns

#### 1. On-Chain KPI Cards

```python
@st.cache_data(ttl=600)  # Cache for 10 min (on-chain data slower)
def _fetch_onchain_metrics(symbol: str):
    return client.fetch_onchain_metrics(symbol)

metrics = _fetch_onchain_metrics(symbol)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Hashrate (BTC)",
        f"{metrics['hashrate']['value']:.0f} EH/s",
        delta=f"{metrics['hashrate']['change_7d']:+.1f}%",
    )

with col2:
    st.metric(
        "Active Addresses",
        f"{metrics['active_addresses']['value'] / 1e6:.2f}M",
        delta=f"{metrics['active_addresses']['change_7d']:+.1f}%",
    )

with col3:
    st.metric(
        "BTC Reserve",
        f"{metrics['reserve']['value']:,.0f}",
        delta=f"{metrics['reserve']['change_7d']:+.1f}%",
    )

with col4:
    st.metric(
        "Whale Activity (24h)",
        f"{metrics['whale_tx_24h']} txs",
        delta=f"Avg: ${metrics['whale_avg_value'] / 1e6:.1f}M",
    )
```

#### 2. Hashrate / Active Addresses Time Series

```python
tab_hashrate, tab_addresses, tab_gas = st.tabs(
    ["Hashrate", "Active Addresses", "Gas Fees"])

with tab_hashrate:
    hashrate_data = client.fetch_onchain_timeseries("BTC", "hashrate", period="7d")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hashrate_data["dates"],
        y=hashrate_data["values"],
        mode='lines+markers',
        name='Hashrate (EH/s)',
        fill='tozeroy',
        line=dict(color="#22d3ee", width=2),
    ))
    fig.update_layout(
        title="BTC Hashrate (7d)",
        yaxis_title="EH/s",
        xaxis_title="Date",
        hovermode='x unified',
        height=350,
        **_DARK_LAYOUT
    )
    st.plotly_chart(fig, use_container_width=True)
```

#### 3. Whale Transactions Table

```python
whale_txs = client.fetch_whale_transactions(symbol="BTC", hours=48, min_amount=500)

whale_df = pd.DataFrame([
    {
        "Time": tx["time_ago"],
        "Amount (BTC)": f"{tx['amount']:,.2f}",
        "USD Value": f"${tx['usd_value'] / 1e6:.1f}M",
        "From": tx["from_label"],
        "To": tx["to_label"],
        "Status": "✅ Confirmed" if tx["confirmed"] else "⏳ Pending",
    }
    for tx in whale_txs
])

st.dataframe(whale_df, use_container_width=True, hide_index=True)

# Download option
csv_data = whale_df.to_csv(index=False).encode('utf-8')
st.download_button("Download whale transactions", csv_data, "whale_tx.csv", "text/csv")
```

---

### Data Model (API Contract)

**GET `/api/v1/onchain/metrics/{symbol}?period=7d`**
```json
{
  "symbol": "BTC",
  "hashrate": {
    "value": 426.5,
    "unit": "EH/s",
    "change_7d": 2.3,
    "timestamp": "2026-03-14T12:00:00Z"
  },
  "active_addresses": {
    "value": 1230000,
    "change_7d": -1.2
  },
  "reserve": {
    "value": 2134452,
    "change_7d": 0.8
  },
  "whale_tx_24h": 8,
  "whale_avg_value": 1500000
}
```

**GET `/api/v1/onchain/timeseries/{symbol}/{metric}?period=7d`**
```json
{
  "symbol": "BTC",
  "metric": "hashrate",
  "period": "7d",
  "data": [
    {"date": "2026-03-07T00:00:00Z", "value": 410.2},
    {"date": "2026-03-08T00:00:00Z", "value": 415.8},
    ...
  ]
}
```

**GET `/api/v1/onchain/whale-transactions?symbol=BTC&hours=48&min_amount=500`**
```json
{
  "data": [
    {
      "tx_hash": "abc123...",
      "time_ago": "2h",
      "amount": 2500,
      "usd_value": 108000000,
      "from_label": "Gemini",
      "to_label": "Unknown",
      "confirmed": false
    }
  ]
}
```

---

## Feature 5: Regulatory Sources in Veille

### Overview

**Personas:** Sarah (Journalist), Aleksandar (Investor)
**Purpose:** Separate regulatory news (ESMA, SEC, EU, Global) from market news; tag articles with regulatory impact; provide official links to source documents.

### Requirements

- **Regulatory News Filter:** Dedicated filter in Veille for regulatory sources (ESMA/SEC/EU Blockchain Observatory/Global News Agency)
- **Article Badge:** Flag articles as "Regulatory" with jurisdiction badge (🇪🇺 ESMA, 🇺🇸 SEC, 🌍 Global)
- **Impact Level:** High/Medium/Low regulatory impact (auto-detected or manual tag)
- **Source Links:** Direct links to official regulatory documents (PDFs, SEC.gov, ESMA docs)
- **Summary Card:** "Regulatory Summary" card showing latest updates per jurisdiction (weekly digest)

### Architecture Decision

**WHERE TO ADD:** Extend **`2_veille.py`** (News Watch page) with:
1. **Filter:** Add toggle/checkbox for "Show regulatory sources only"
2. **Badge:** Add regulatory badge to news card component
3. **Tab:** Add new tab "Regulatory Digest" alongside existing news/sentiment/keywords

**RATIONALE:** Regulatory news is part of the broader veille. Sarah (journalist) needs to filter & export it. Keeps all news in one place, but with clear visual separation.

---

### Wireframe: Regulatory Tab in Veille

```
╔════════════════════════════════════════════════════════════════════════════╗
║ 📰 Veille Crypto                                                            ║
║ [Filter Bar]                                                                ║
║                                                                              ║
║ [Latest News] [Sentiment] [Keywords] [Regulatory Digest]  (tabs)           ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 📋 REGULATORY DIGEST — Last 30 Days                                  │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │ ┌────────────────────────────────────┐                              │   ║
║  │ │ 🇪🇺 ESMA (Europe)                 │  8 updates this month        │   ║
║  │ │                                    │  Last: 2026-03-12             │   ║
║  │ │ • MiCA compliance deadline April   │                              │   ║
║  │ │ • Leverage ban guidance (Jan 2024) │                              │   ║
║  │ │ • Staking risk warning             │                              │   ║
║  │ │ [Show all] [Subscribe]             │                              │   ║
║  │ └────────────────────────────────────┘                              │   ║
║  │                                                                      │   ║
║  │ ┌────────────────────────────────────┐                              │   ║
║  │ │ 🇺🇸 SEC (United States)            │  5 updates this month        │   ║
║  │ │                                    │  Last: 2026-03-08             │   ║
║  │ │ • ETF approval rumors              │                              │   ║
║  │ │ • Trading halts (penny stocks)     │                              │   ║
║  │ │ • Insider trading investigation    │                              │   ║
║  │ │ [Show all] [Subscribe]             │                              │   ║
║  │ └────────────────────────────────────┘                              │   ║
║  │                                                                      │   ║
║  │ ┌────────────────────────────────────┐                              │   ║
║  │ │ 🌍 GLOBAL & OTHER                 │  12 updates this month       │   ║
║  │ │                                    │  Last: 2026-03-13             │   ║
║  │ │ • FCA (UK) NFT guidance            │                              │   ║
║  │ │ • Hong Kong staking ban            │                              │   ║
║  │ │ • Singapore DeFi oversight         │                              │   ║
║  │ │ [Show all] [Subscribe]             │                              │   ║
║  │ └────────────────────────────────────┘                              │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │ 🔔 LATEST REGULATORY UPDATES                                         │   ║
║  ├──────────────────────────────────────────────────────────────────────┤   ║
║  │                                                                      │   ║
║  │ [🇪🇺 ESMA] [🇺🇸 SEC] [🌍 Global] [All]  [Sort by: Date | Impact]   │   ║
║  │                                                                      │   ║
║  │ 🇪🇺 [HIGH] ESMA MiCA Compliance Rules — Final Guidelines             │   ║
║  │ Published: 2026-03-12 | Source: esma.europa.eu                     │   ║
║  │                                                                      │   ║
║  │ Summary: ESMA clarifies implementation timelines for Markets in     │   ║
║  │ Crypto-assets regulation. Critical for all EU-regulated platforms. │   ║
║  │ Key points:                                                         │   ║
║  │ • Trading account segregation mandatory by June 2026               │   ║
║  │ • Market manipulation controls required (AI-based OK)              │   ║
║  │ • Staking providers must declare reward risks                       │   ║
║  │                                                                      │   ║
║  │ Impact: HIGH — Affects all EU players. Implementation cost: medium │   ║
║  │                                                                      │   ║
║  │ [📄 Official PDF] [Full article] [Discuss] [Save to library]       │   ║
║  │                                                                      │   ║
║  │ ────────────────────────────────────────────────────────────────────│   ║
║  │                                                                      │   ║
║  │ 🇺🇸 [HIGH] SEC Chair Powell: Crypto Needs Oversight Framework      │   ║
║  │ Published: 2026-03-08 | Source: SEC.gov testimony                  │   ║
║  │                                                                      │   ║
║  │ Key Points:                                                         │   ║
║  │ • Existing laws likely sufficient for crypto regulation            │   ║
║  │ • Congress should clarify CFTC vs SEC jurisdiction                 │   ║
║  │ • Staking perceived as securities issuance (no change from 2024)  │   ║
║  │                                                                      │   ║
║  │ Impact: MEDIUM — Regulatory clarity improving slowly               │   ║
║  │                                                                      │   ║
║  │ [📄 Official Testimony] [Full article] [Discuss] [Save]            │   ║
║  │                                                                      │   ║
║  │ ────────────────────────────────────────────────────────────────────│   ║
║  │                                                                      │   ║
║  │ 🌍 [MEDIUM] Hong Kong: Staking Rewards Debate Continues            │   ║
║  │ Published: 2026-02-28 | Source: Hong Kong Monetary Authority       │   ║
║  │                                                                      │   ║
║  │ [Show more regulatory articles...]                                  │   ║
║  │                                                                      │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

### Key Components & Streamlit Patterns

#### 1. Regulatory Filter in Filter Bar (2_veille.py)

```python
# Extend the existing filter bar
with st.container(border=True):
    col_source, col_keyword = st.columns([1, 2])
    with col_source:
        all_label = t("veille.all_sources")
        # Add regulatory option
        sources = [
            all_label,
            "Regulatory",  # NEW
            *_SOURCES_RAW,
        ]
        source = st.selectbox(t("veille.source"), sources, index=0)
    with col_keyword:
        keyword = st.text_input(t("veille.keyword"), placeholder=t("veille.keyword_placeholder"))

    # NEW: Regulatory jurisdiction filter
    if source == "Regulatory":
        jurisdictions = st.multiselect(
            "Regulatory Jurisdictions",
            ["ESMA (Europe)", "SEC (USA)", "FCA (UK)", "Global"],
            default=["ESMA (Europe)", "SEC (USA)"],
        )

    # Date range (unchanged)
    col_date_from, col_date_to = st.columns([1, 1])
    with col_date_from:
        date_from = st.date_input(t("veille.date_from"), ...)
    with col_date_to:
        date_to = st.date_input(t("veille.date_to"), ...)
```

#### 2. Regulatory Tab in Veille

```python
tab_latest, tab_sentiment, tab_keywords, tab_regulatory = st.tabs([
    t("veille.latest_news"),
    t("veille.sentiment_by_source"),
    t("veille.trending_keywords"),
    "Regulatory Digest",  # NEW
])

with tab_regulatory:
    _render_regulatory_digest()
```

#### 3. Regulatory Digest Component

```python
def _render_regulatory_digest():
    """Render regulatory summary cards by jurisdiction."""
    digest = client.fetch_regulatory_digest(period="30d")

    # Summary cards
    col_esma, col_sec, col_global = st.columns(3)

    with col_esma:
        with st.container(border=True):
            st.markdown("### 🇪🇺 ESMA (Europe)")
            st.metric(
                "Updates this month",
                digest["esma"]["count"],
                delta=f"Last: {digest['esma']['last_date']}"
            )
            st.markdown(f"**Impact:** {digest['esma']['avg_impact']}")
            for item in digest["esma"]["latest_items"][:3]:
                st.markdown(f"• {item['title']}")
            if st.button("Show all", key="show_esma"):
                st.session_state["show_esma"] = True

    with col_sec:
        with st.container(border=True):
            st.markdown("### 🇺🇸 SEC (USA)")
            st.metric(
                "Updates this month",
                digest["sec"]["count"],
                delta=f"Last: {digest['sec']['last_date']}"
            )
            st.markdown(f"**Impact:** {digest['sec']['avg_impact']}")
            for item in digest["sec"]["latest_items"][:3]:
                st.markdown(f"• {item['title']}")

    with col_global:
        with st.container(border=True):
            st.markdown("### 🌍 Global & Other")
            st.metric(
                "Updates this month",
                digest["global"]["count"],
                delta=f"Last: {digest['global']['last_date']}"
            )
            st.markdown(f"**Impact:** {digest['global']['avg_impact']}")
            for item in digest["global"]["latest_items"][:3]:
                st.markdown(f"• {item['title']}")

    st.divider()

    # Full list with filtering
    st.markdown("### 📰 Latest Regulatory Updates")

    # Filter tabs
    tab_all, tab_high, tab_medium = st.tabs(["All", "High Impact", "Medium Impact"])

    with tab_all:
        _render_regulatory_articles(digest["articles"])
    with tab_high:
        _render_regulatory_articles([a for a in digest["articles"] if a["impact"] == "HIGH"])
    with tab_medium:
        _render_regulatory_articles([a for a in digest["articles"] if a["impact"] == "MEDIUM"])


def _render_regulatory_articles(articles):
    """Render regulatory articles with impact badges and official links."""
    for article in articles:
        impact_color = "#f85149" if article["impact"] == "HIGH" else "#d29922"
        jurisdiction_icon = {
            "ESMA": "🇪🇺",
            "SEC": "🇺🇸",
            "FCA": "🇬🇧",
            "Global": "🌍",
        }.get(article["jurisdiction"], "📋")

        with st.container(border=True):
            col_badge, col_title = st.columns([1, 3])
            with col_badge:
                st.markdown(f"### {jurisdiction_icon}")
                st.markdown(
                    f"<span style='color:{impact_color};font-weight:bold;'>"
                    f"{article['impact']}</span>",
                    unsafe_allow_html=True
                )
            with col_title:
                st.markdown(f"### {article['title']}")
                st.caption(f"Published: {article['published_at']} | Source: {article['source_url']}")

            st.markdown(article["summary"])

            # Key points
            st.markdown("**Key Points:**")
            for point in article["key_points"][:5]:
                st.markdown(f"• {point}")

            # Action buttons
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(
                    f"[📄 Official Document]({article['official_url']})",
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(f"[📖 Full Article]({article['article_url']})")
            with col3:
                if st.button("💾 Save to library", key=f"save_{article['id']}"):
                    client.save_article_to_library(article['id'])
                    st.success("Saved!")
            with col4:
                if st.button("💬 Discuss", key=f"discuss_{article['id']}"):
                    st.session_state["show_discussion"] = article['id']
```

#### 4. Updated News Card Component (with regulatory badge)

```python
# In components/news_feed.py
def render_news_card(article: dict[str, Any]) -> None:
    """Render a news card with optional regulatory badge."""

    # Determine if regulatory
    is_regulatory = article.get("is_regulatory", False)
    jurisdiction = article.get("jurisdiction")  # "ESMA", "SEC", "FCA", "Global"
    impact = article.get("regulatory_impact")   # "HIGH", "MEDIUM", "LOW"

    with st.container(border=True):
        # Header with badges
        col_badges, col_title = st.columns([1, 3])

        with col_badges:
            if is_regulatory:
                icon_map = {
                    "ESMA": "🇪🇺",
                    "SEC": "🇺🇸",
                    "FCA": "🇬🇧",
                    "Global": "🌍",
                }
                st.markdown(f"{icon_map.get(jurisdiction, '📋')}")
                st.markdown(f"<small style='color:#d29922;font-weight:bold;'>REG</small>",
                           unsafe_allow_html=True)

        with col_title:
            st.markdown(f"**{article.get('title', 'Untitled')}**")

        # Metadata
        st.caption(
            f"{article.get('source', 'Unknown')} • "
            f"{article.get('published_at', 'N/A')}"
        )

        # Summary
        st.markdown(article.get("summary", article.get("description", "")))

        # Tags
        keywords = article.get("keywords", [])
        if keywords:
            st.markdown(" ".join([f"`{kw}`" for kw in keywords[:5]]))

        # Footer with actions
        col_sentiment, col_actions = st.columns([1, 2])

        with col_sentiment:
            sentiment = article.get("sentiment_score")
            if sentiment is not None:
                sentiment_pct = int(sentiment * 100)
                sentiment_emoji = "😊" if sentiment > 0.5 else "😐" if sentiment > -0.5 else "😞"
                st.markdown(f"{sentiment_emoji} {sentiment_pct}%")

        with col_actions:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"[Read →]({article.get('url', '#')})")
            with col_b:
                if st.button("🔔 Alert", key=f"alert_{article.get('id', 'unknown')}"):
                    # Create alert rule based on this article
                    st.session_state["new_alert_from_article"] = article['id']
```

---

### Data Model (API Contract)

**GET `/api/v1/news/regulatory-digest?period=30d`**
```json
{
  "esma": {
    "count": 8,
    "last_date": "2026-03-12",
    "avg_impact": "HIGH",
    "latest_items": [
      {"title": "MiCA Compliance Rules", "date": "2026-03-12"},
      {"title": "Leverage Guidance Update", "date": "2026-03-05"}
    ]
  },
  "sec": {
    "count": 5,
    "last_date": "2026-03-08",
    "avg_impact": "MEDIUM",
    "latest_items": [...]
  },
  "global": {
    "count": 12,
    "last_date": "2026-03-13",
    "avg_impact": "MEDIUM",
    "latest_items": [...]
  },
  "articles": [
    {
      "id": "reg_123",
      "title": "ESMA MiCA Final Guidelines",
      "jurisdiction": "ESMA",
      "impact": "HIGH",
      "published_at": "2026-03-12T10:30:00Z",
      "source_url": "esma.europa.eu",
      "official_url": "https://esma.europa.eu/.../micarules.pdf",
      "article_url": "https://cointelegraph.com/news/esma-micarules",
      "summary": "ESMA clarifies implementation timelines...",
      "key_points": [
        "Trading account segregation mandatory by June 2026",
        "Market manipulation controls required"
      ]
    }
  ]
}
```

**GET `/api/v1/news?source=regulatory&jurisdiction=ESMA,SEC`**
```json
{
  "data": [
    {
      "id": "reg_123",
      "title": "...",
      "is_regulatory": true,
      "jurisdiction": "ESMA",
      "regulatory_impact": "HIGH",
      "official_url": "https://...",
      "...": "... (standard news fields)"
    }
  ]
}
```

---

## User Flows & Personas

### Noah (Trader) — Full Workflow

**Goal:** Use CryptoBot to scout signals, backtest with paper trading, export trades, export alerts.

```
1. Login
   ↓
2. Dashboard: Select BTC/4h
   • View candlestick + RSI/BB indicators
   • See latest news for context
   • Check on-chain metrics (hashrate, whale activity)
   ↓
3. See BTC signal: "LONG, RSI 4h > 70, confidence 0.87"
   ↓
4. Paper Trading Page: Place order
   • BTC, LONG, 0.2 qty, entry current, SL -5%, TP +5%/+8%/+10%
   • Check equity curve (no major draw-down)
   • Submit
   ↓
5. Alerts Page: Create new alert
   • "Notify me when BTC falls below $40k (support break)"
   • Channels: Email + In-app
   ↓
6. Performance Page: Export closed trades
   • See win rate 65%, avg win $1,200, Sharpe 1.8
   • Download trades.csv for journal
   ↓
7. Veille Page: Stay updated
   • Check regulatory news (ESMA MiCA) for risk assessment
   • Export news.csv for trading diary
```

### Sarah (Journalist) — Workflow

**Goal:** Monitor news, filter regulatory sources, export summaries, write articles.

```
1. Login / Browse (no auth required for news)
   ↓
2. Veille Page: Open "Regulatory Digest" tab
   • See ESMA/SEC/Global cards with latest updates
   • Click ESMA card to expand full articles
   ↓
3. Filter: "Show ESMA + SEC only, last 7 days"
   • Export as CSV for article research
   ↓
4. Click on regulatory article
   • Read summary, key points
   • Open official PDF (ESMA.europa.eu)
   • Check impact level (HIGH = must cover)
   ↓
5. Save articles to library
   • Use as research material for weekly digest
   ↓
6. Sentiment analysis
   • View sentiment by source for opinion polling
   • Word cloud for trending topics
```

### Aleksandar (Investor) — Workflow

**Goal:** Monitor portfolio, track long-term P&L, use chatbot for analysis, backtesting.

```
1. Login
   ↓
2. Portfolio Tab: See real holdings
   • ETH: 5 qty, entry $2,300, current $2,180, -$600 USD
   • BTC: 0.5 qty, entry $42,100, current $43,250, +$575 USD
   • Watchlist: SOL, AVAX, ADA
   ↓
3. Paper Trading: Backtest a "LONG SOL at $125 if RSI < 40" strategy
   • Simulate from 2025-01-01 to now
   • See backtest equity curve, max drawdown
   • Decide whether to trade live (or keep paper only)
   ↓
4. Analytics Page: Check regime + clustering
   • Regime: BULL (78% strength)
   • Cluster: ETH + SOL correlated (0.68) → diversify to ADA (lower corr)
   ↓
5. Chatbot: Ask "Should I increase BTC position given current regime?"
   • Chatbot summarizes bull sentiment, suggests 2x allocation with caution
   ↓
6. Alerts: Set "Notify if BTC breaks below $40k (support)"
   • Track risk levels on positions
```

---

## i18n (FR/EN Labels)

Add these translations to `src/frontend/i18n/en.py` and `fr.py`:

### English (en.py)

```python
# Paper Trading
"paper_trading.header": "Paper Trading Journal",
"paper_trading.balance": "Account Balance",
"paper_trading.invested": "Invested",
"paper_trading.available": "Available",
"paper_trading.total_pnl": "Total P&L",
"paper_trading.pnl_pct": "P&L %",
"paper_trading.realized_pnl": "Realized P&L",
"paper_trading.unrealized_pnl": "Unrealized P&L",
"paper_trading.max_drawdown": "Max Drawdown",
"paper_trading.open_positions": "Open Positions",
"paper_trading.closed_trades": "Closed Trades Journal",
"paper_trading.place_new_trade": "Place New Trade",
"paper_trading.symbol": "Symbol",
"paper_trading.direction": "Direction",
"paper_trading.quantity": "Quantity",
"paper_trading.entry_price": "Entry Price",
"paper_trading.stop_loss": "Stop Loss",
"paper_trading.take_profit": "Take Profit",
"paper_trading.leverage": "Leverage",
"paper_trading.memo": "Trade Memo (optional)",
"paper_trading.place_trade_button": "Place Trade",
"paper_trading.col_symbol": "Symbol",
"paper_trading.col_direction": "Direction",
"paper_trading.col_entry": "Entry",
"paper_trading.col_current": "Current",
"paper_trading.col_qty": "Qty",
"paper_trading.col_pnl": "P&L %",
"paper_trading.col_sl": "SL",
"paper_trading.col_tp": "TP",
"paper_trading.col_action": "Action",
"paper_trading.close_position": "Close",
"paper_trading.edit_position": "Edit",
"paper_trading.col_date": "Date",
"paper_trading.col_outcome": "Outcome",
"paper_trading.col_hold_time": "Hold Time",
"paper_trading.equity_curve": "Equity Curve",
"paper_trading.drawdown_analysis": "Drawdown Analysis",
"paper_trading.statistics": "Statistics",
"paper_trading.win_rate": "Win Rate",
"paper_trading.avg_win": "Avg Win",
"paper_trading.avg_loss": "Avg Loss",
"paper_trading.sharpe_ratio": "Sharpe Ratio",
"paper_trading.calmar_ratio": "Calmar Ratio",
"paper_trading.export_trades": "Export Trades as CSV",

# Alerts
"alerts.header": "Alerts & Notifications",
"alerts.unread_count": "Unread",
"alerts.tab_rules": "Alert Rules",
"alerts.tab_history": "History",
"alerts.tab_preferences": "Preferences",
"alerts.create_rule": "Create New Rule",
"alerts.rule_name": "Rule Name",
"alerts.trigger_type": "Trigger Type",
"alerts.price_alert": "Price Alert",
"alerts.indicator_alert": "Indicator Alert",
"alerts.regime_change": "Regime Change",
"alerts.regulatory_news": "Regulatory News",
"alerts.symbol": "Symbol",
"alerts.indicator": "Indicator",
"alerts.operator": "Operator",
"alerts.value": "Value",
"alerts.frequency": "Frequency",
"alerts.notify_via": "Notify via",
"alerts.in_app": "In-app",
"alerts.email": "Email",
"alerts.telegram": "Telegram",
"alerts.sms": "SMS",
"alerts.enabled": "Enabled",
"alerts.disabled": "Disabled",
"alerts.last_triggered": "Last triggered",
"alerts.trigger_count": "Triggers this month",
"alerts.test_trigger": "Test trigger",
"alerts.delete_rule": "Delete rule",
"alerts.alert_history": "Alert History",
"alerts.alert_time": "Time",
"alerts.alert_condition": "Condition",
"alerts.triggered_value": "Triggered Value",
"alerts.alert_status": "Status",
"alerts.mark_as_read": "Mark as read",
"alerts.mark_as_unread": "Mark as unread",
"alerts.clear_all": "Clear all",
"alerts.no_alerts": "No unread alerts",

# Clustering & Regime
"analytics.regime_title": "Market Regime",
"analytics.regime_bull": "Bull Market",
"analytics.regime_bear": "Bear Market",
"analytics.regime_sideways": "Sideways",
"analytics.regime_strength": "Regime Strength",
"analytics.supporting_indicators": "Supporting Indicators",
"analytics.regime_timeline": "Regime Timeline",
"analytics.regime_changes": "Regime Changes",
"analytics.cluster_map": "Cluster Map",
"analytics.cluster_assets": "Assets",
"analytics.cluster_avg_corr": "Avg Correlation",
"analytics.cluster_volatility": "Volatility",
"analytics.clustering_tab": "Clustering",
"analytics.regime_tab": "Regime",

# On-Chain Metrics
"dashboard.onchain_header": "On-Chain Metrics",
"dashboard.onchain_toggle": "Show on-chain data",
"dashboard.hashrate": "Hashrate",
"dashboard.active_addresses": "Active Addresses",
"dashboard.btc_reserve": "BTC Reserve",
"dashboard.whale_activity": "Whale Activity",
"dashboard.gas_fees": "Gas Fees",
"dashboard.exchange_netflow": "Exchange Netflow",
"dashboard.whale_transactions": "Top Whale Transactions",
"dashboard.whale_amount": "Amount",
"dashboard.whale_from": "From",
"dashboard.whale_to": "To",
"dashboard.whale_status": "Status",

# Regulatory News
"veille.regulatory_digest": "Regulatory Digest",
"veille.regulatory_filter": "Regulatory sources",
"veille.jurisdiction": "Jurisdiction",
"veille.esma": "ESMA (Europe)",
"veille.sec": "SEC (USA)",
"veille.fca": "FCA (UK)",
"veille.global_regulatory": "Global & Other",
"veille.regulatory_impact": "Regulatory Impact",
"veille.official_document": "Official Document",
"veille.key_points": "Key Points",
"veille.save_to_library": "Save to library",
```

### French (fr.py)

```python
# Paper Trading
"paper_trading.header": "Journal de Trading Simulé",
"paper_trading.balance": "Solde du compte",
"paper_trading.invested": "Investi",
"paper_trading.available": "Disponible",
"paper_trading.total_pnl": "P&L Total",
"paper_trading.pnl_pct": "P&L %",
"paper_trading.realized_pnl": "P&L Réalisé",
"paper_trading.unrealized_pnl": "P&L Non-réalisé",
"paper_trading.max_drawdown": "Drawdown Max",
"paper_trading.open_positions": "Positions Ouvertes",
"paper_trading.closed_trades": "Journal des Trades Fermés",
"paper_trading.place_new_trade": "Placer un Nouveau Trade",
"paper_trading.symbol": "Symbole",
"paper_trading.direction": "Direction",
"paper_trading.quantity": "Quantité",
"paper_trading.entry_price": "Prix d'entrée",
"paper_trading.stop_loss": "Stop Loss",
"paper_trading.take_profit": "Take Profit",
"paper_trading.leverage": "Levier",
"paper_trading.memo": "Mémo du trade (optionnel)",
"paper_trading.place_trade_button": "Placer le trade",
"paper_trading.col_symbol": "Symbole",
"paper_trading.col_direction": "Direction",
"paper_trading.col_entry": "Entrée",
"paper_trading.col_current": "Actuel",
"paper_trading.col_qty": "Qté",
"paper_trading.col_pnl": "P&L %",
"paper_trading.col_sl": "SL",
"paper_trading.col_tp": "TP",
"paper_trading.col_action": "Action",
"paper_trading.close_position": "Fermer",
"paper_trading.edit_position": "Éditer",
"paper_trading.col_date": "Date",
"paper_trading.col_outcome": "Résultat",
"paper_trading.col_hold_time": "Durée",
"paper_trading.equity_curve": "Courbe d'équité",
"paper_trading.drawdown_analysis": "Analyse du Drawdown",
"paper_trading.statistics": "Statistiques",
"paper_trading.win_rate": "Taux de gain",
"paper_trading.avg_win": "Gain moyen",
"paper_trading.avg_loss": "Perte moyenne",
"paper_trading.sharpe_ratio": "Ratio de Sharpe",
"paper_trading.calmar_ratio": "Ratio de Calmar",
"paper_trading.export_trades": "Exporter les trades en CSV",

# Alerts
"alerts.header": "Alertes & Notifications",
"alerts.unread_count": "Non lu",
"alerts.tab_rules": "Règles d'alerte",
"alerts.tab_history": "Historique",
"alerts.tab_preferences": "Préférences",
"alerts.create_rule": "Créer une nouvelle règle",
"alerts.rule_name": "Nom de la règle",
"alerts.trigger_type": "Type de déclencheur",
"alerts.price_alert": "Alerte de prix",
"alerts.indicator_alert": "Alerte indicateur",
"alerts.regime_change": "Changement de régime",
"alerts.regulatory_news": "Actualités réglementaires",
"alerts.symbol": "Symbole",
"alerts.indicator": "Indicateur",
"alerts.operator": "Opérateur",
"alerts.value": "Valeur",
"alerts.frequency": "Fréquence",
"alerts.notify_via": "Notifier via",
"alerts.in_app": "In-app",
"alerts.email": "Email",
"alerts.telegram": "Telegram",
"alerts.sms": "SMS",
"alerts.enabled": "Activé",
"alerts.disabled": "Désactivé",
"alerts.last_triggered": "Déclenché pour la dernière fois",
"alerts.trigger_count": "Déclenchements ce mois-ci",
"alerts.test_trigger": "Tester le déclencheur",
"alerts.delete_rule": "Supprimer la règle",
"alerts.alert_history": "Historique des alertes",
"alerts.alert_time": "Heure",
"alerts.alert_condition": "Condition",
"alerts.triggered_value": "Valeur déclenchée",
"alerts.alert_status": "Statut",
"alerts.mark_as_read": "Marquer comme lu",
"alerts.mark_as_unread": "Marquer comme non lu",
"alerts.clear_all": "Effacer tout",
"alerts.no_alerts": "Pas d'alertes non lues",

# Clustering & Regime
"analytics.regime_title": "Régime de marché",
"analytics.regime_bull": "Marché haussier",
"analytics.regime_bear": "Marché baissier",
"analytics.regime_sideways": "Consolidation",
"analytics.regime_strength": "Force du régime",
"analytics.supporting_indicators": "Indicateurs de support",
"analytics.regime_timeline": "Chronologie des régimes",
"analytics.regime_changes": "Changements de régime",
"analytics.cluster_map": "Carte de clustering",
"analytics.cluster_assets": "Actifs",
"analytics.cluster_avg_corr": "Corrélation moy",
"analytics.cluster_volatility": "Volatilité",
"analytics.clustering_tab": "Clustering",
"analytics.regime_tab": "Régime",

# On-Chain Metrics
"dashboard.onchain_header": "Métriques On-Chain",
"dashboard.onchain_toggle": "Afficher les données on-chain",
"dashboard.hashrate": "Hashrate",
"dashboard.active_addresses": "Adresses actives",
"dashboard.btc_reserve": "Réserves BTC",
"dashboard.whale_activity": "Activité des baleines",
"dashboard.gas_fees": "Frais de gaz",
"dashboard.exchange_netflow": "Flux net des exchanges",
"dashboard.whale_transactions": "Top transactions de baleine",
"dashboard.whale_amount": "Montant",
"dashboard.whale_from": "Depuis",
"dashboard.whale_to": "Vers",
"dashboard.whale_status": "Statut",

# Regulatory News
"veille.regulatory_digest": "Résumé réglementaire",
"veille.regulatory_filter": "Sources réglementaires",
"veille.jurisdiction": "Juridiction",
"veille.esma": "ESMA (Europe)",
"veille.sec": "SEC (USA)",
"veille.fca": "FCA (UK)",
"veille.global_regulatory": "Global & Autres",
"veille.regulatory_impact": "Impact réglementaire",
"veille.official_document": "Document officiel",
"veille.key_points": "Points clés",
"veille.save_to_library": "Sauvegarder dans la bibliothèque",
```

---

## Implementation Checklist

### Phase 1: Paper Trading (Priority HIGH)

- [ ] Create `src/frontend/pages/6_paper_trading.py`
  - [ ] Account summary metrics (balance, P&L, drawdown)
  - [ ] Equity curve chart (daily, period selector)
  - [ ] Open positions table with close/edit buttons
  - [ ] Place trade form with validation
  - [ ] Closed trades journal with CSV export
  - [ ] Statistics tab (win rate, Sharpe, etc.)
- [ ] Create `src/frontend/components/paper_trading.py` (optional, if reusable)
- [ ] Update `src/frontend/app.py` to add new page to navigation
- [ ] Add i18n labels to `en.py` and `fr.py`
- [ ] Update API client with paper trading endpoints
- [ ] **Test:** Place order → verify balance updated → close position → verify P&L calculated

### Phase 2: Alerts (Priority HIGH)

- [ ] Create `src/frontend/pages/7_alerts.py`
  - [ ] Rules management tab (create, edit, disable, test)
  - [ ] Alert history tab with filtering
  - [ ] Preferences tab (notification channels)
- [ ] Create `src/frontend/components/alert_rule_builder.py` (multi-step form)
- [ ] Add sidebar badge + toast notifications to `app.py`
- [ ] Add to all pages: unread alert indicator
- [ ] Update API client with alert endpoints
- [ ] **Test:** Create rule → trigger condition → verify notification

### Phase 3: Clustering & Regime (Priority MEDIUM)

- [ ] Extend `src/frontend/pages/4_analytics.py`
  - [ ] Add "Regime" tab (gauge + supporting indicators + timeline)
  - [ ] Add "Clustering" tab (scatter plot + cluster metrics)
- [ ] Update API client with clustering/regime endpoints
- [ ] **Test:** Verify cluster visualization loads; regime indicator updates daily

### Phase 4: On-Chain Metrics (Priority MEDIUM)

- [ ] Extend `src/frontend/pages/1_dashboard.py`
  - [ ] Add collapsible "On-Chain Metrics" section below candlestick
  - [ ] KPI cards (hashrate, active addresses, whale activity)
  - [ ] Time series charts (hashrate, addresses, gas fees)
  - [ ] Whale transactions table
- [ ] Update API client with on-chain endpoints
- [ ] **Test:** Toggle on-chain section; verify data loads for multiple symbols

### Phase 5: Regulatory News (Priority MEDIUM)

- [ ] Extend `src/frontend/pages/2_veille.py`
  - [ ] Add "Regulatory Digest" tab
  - [ ] Extend filter bar with regulatory jurisdiction selector
  - [ ] Add regulatory badges to news cards
  - [ ] Regulatory summary cards (ESMA, SEC, Global)
- [ ] Update `src/frontend/components/news_feed.py` to render regulatory badges
- [ ] Update API client with regulatory news endpoints
- [ ] **Test:** Filter by regulatory source; verify badges render

### Cross-Cutting Tasks

- [ ] **i18n:** Add all new labels to `en.py` and `fr.py`
- [ ] **Component extraction:** Move reusable patterns into `src/frontend/components/` (e.g., metric cards, form builders)
- [ ] **Error handling:** Add `try/except` around API calls; surface errors as `st.error()`
- [ ] **Caching:** Use `@st.cache_data(ttl=N)` appropriately (300s for on-chain, 60s for price/indicators, 30s for alerts)
- [ ] **Testing:** Write unit tests for data formatting functions; E2E for full workflows (Noah's trade → alert workflow)
- [ ] **Documentation:** Update `docs/04-frontend-ui.md` with new page descriptions and API contracts

### API Requirements (Backend)

Ensure the backend implements these endpoints:

**Paper Trading:**
- `GET /api/v1/paper-trading/account`
- `GET /api/v1/paper-trading/positions?status=open|closed`
- `POST /api/v1/paper-trading/positions`
- `PATCH /api/v1/paper-trading/positions/{id}`
- `DELETE /api/v1/paper-trading/positions/{id}`
- `GET /api/v1/paper-trading/equity-curve?period=7d|30d|90d|YTD|ALL`
- `GET /api/v1/paper-trading/statistics`

**Alerts:**
- `GET /api/v1/alerts/rules`
- `POST /api/v1/alerts/rules`
- `PATCH /api/v1/alerts/rules/{id}`
- `DELETE /api/v1/alerts/rules/{id}`
- `POST /api/v1/alerts/rules/{id}/test`
- `GET /api/v1/alerts/history?limit=50&unread=true|false`
- `PATCH /api/v1/alerts/{id}/mark-read`
- `GET /api/v1/alerts/unread-count`

**Clustering & Regime:**
- `GET /api/v1/analytics/regime`
- `GET /api/v1/analytics/clustering`
- `GET /api/v1/analytics/regime-history?days=30`

**On-Chain:**
- `GET /api/v1/onchain/metrics/{symbol}?period=7d|30d`
- `GET /api/v1/onchain/timeseries/{symbol}/{metric}?period=7d|30d`
- `GET /api/v1/onchain/whale-transactions?symbol=BTC&hours=48&min_amount=500`

**Regulatory News:**
- `GET /api/v1/news/regulatory-digest?period=30d`
- Extend `GET /api/v1/news?source=regulatory&jurisdiction=ESMA,SEC`

---

## Design Decisions & Rationale

| Feature | Decision | Rationale |
|---------|----------|-----------|
| **Paper Trading** | New page (6_paper_trading.py) | Complete feature deserving dedicated space; Noah's integrated workflow |
| **Alerts** | New page (7_alerts.py) + sidebar badge | Cross-cutting concern; sidebar badge for visibility everywhere |
| **Regime/Clustering** | Extend Analytics page | Market-level analysis already in Analytics; keeps structure coherent |
| **On-Chain Metrics** | Extend Dashboard | Noah wants integrated price+news+on-chain view; collapsible section keeps it optional |
| **Regulatory News** | Extend Veille page | Regulatory alerts belong in news monitoring; tab separation for Sarah's workflow |
| **i18n** | FR + EN labels | Support bilingual users (Noah, Sarah, Aleksandar in BMAD team) |

---

## Next Steps

1. **Backend team** to review API contracts and implement endpoints
2. **Frontend engineer** to start Phase 1 (Paper Trading) — highest value for Noah
3. **UX team** to validate wireframes with users (especially Aleksandar for backtest workflow)
4. **QA team** to write E2E tests for critical user flows (trade placement, alert triggering, regime changes)

---

**Questions?** Reach out to the Product team for clarifications on requirements or user workflows.
