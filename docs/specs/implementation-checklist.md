# Checklist d'Implémentation — Nouveaux Composants

> Utiliser ce document pour tracker la progression. Chaque équipe maintient sa propre section.

---

## 1. PAPER TRADING ENGINE

**Équipe Responsable** : Backend (API)

### Database & Migrations
- [ ] Créer migration Alembic pour `paper_accounts`, `paper_orders`, `paper_positions`, `paper_trades`
  - File: `src/etl/migrations/versions/xxx_add_paper_trading_tables.py`
  - Test: `psql` connexion, `\dt` pour vérifier les tables

- [ ] Vérifier indexes & constraints
  ```bash
  psql -U cryptobot -d cryptobot -c "SELECT indexname FROM pg_indexes WHERE tablename = 'paper_accounts';"
  ```

### Pydantic Models
- [ ] Créer `src/shared/models/paper_trading.py`
  - [ ] `PaperAccountCreate`, `PaperAccountRead`
  - [ ] `PaperOrderCreate`, `PaperOrderRead`
  - [ ] `PaperPositionRead`, `PaperTradeRead`
  - [ ] Validator pour leverage (1-10), quantity (>0)
  - [ ] Test: `pytest tests/unit/test_shared/test_paper_trading_models.py`

### ORM Models
- [ ] Update `src/shared/db_models.py`
  - [ ] Add `PaperAccountOrm`, `PaperOrderOrm`, `PaperPositionOrm`, `PaperTradeOrm`
  - [ ] Add relationships in `UserOrm`
  - [ ] Test: `pytest tests/unit/test_shared/test_orm_models.py`

### FastAPI Service
- [ ] Créer `src/api/services/paper_trading_service.py`
  - [ ] `create_account(user_id, account_name, initial_balance)`
  - [ ] `get_account(account_id)` with balance + P&L
  - [ ] `create_order(account_id, signal_id, symbol, side, order_type, quantity, entry_price, sl, tp, leverage)`
  - [ ] `validate_order(account_id, order)` → check margin, leverage, funds
  - [ ] `get_orders(account_id, status=None)` with pagination
  - [ ] `get_trades(account_id)` with pagination
  - [ ] `calculate_performance(account_id)` → total P&L, win rate, Sharpe ratio
  - [ ] Type hints everywhere; use `AsyncSession` for all DB queries
  - [ ] Test: `pytest tests/unit/test_api/test_paper_trading_service.py -v`

### FastAPI Router
- [ ] Créer `src/api/routers/paper_trading.py`
  - [ ] POST `/api/v1/paper-trading/accounts` → create account
  - [ ] GET `/api/v1/paper-trading/accounts/{account_id}` → get account
  - [ ] GET `/api/v1/paper-trading/accounts/{account_id}/positions` → list open positions
  - [ ] GET `/api/v1/paper-trading/accounts/{account_id}/trades` → list trades (pagination)
  - [ ] GET `/api/v1/paper-trading/accounts/{account_id}/performance` → metrics
  - [ ] POST `/api/v1/paper-trading/orders` → place order
  - [ ] PUT `/api/v1/paper-trading/orders/{order_id}/cancel` → cancel pending order
  - [ ] GET `/api/v1/paper-trading/orders/{order_id}` → get order status
  - [ ] Auth: `@Depends(get_current_user)` on all endpoints
  - [ ] Error handling: 400 (validation), 404 (not found), 422 (insufficient margin)
  - [ ] Response model: `ApiResponse[T]` envelope
  - [ ] Test: `pytest tests/integration/test_api/test_paper_trading_endpoints.py -v`

### Integration with Main API
- [ ] Update `src/api/main.py`
  ```python
  from src.api.routers import paper_trading
  app.include_router(paper_trading.router, tags=["paper_trading"])
  ```

### Paper Trading Executor Worker
- [ ] Créer `src/api/workers/paper_trading_executor.py`
  - [ ] Class `PaperTradingExecutor`
  - [ ] Method: `execute_orders_for_symbol(symbol, current_price)` async
  - [ ] Logic:
    1. Fetch all open orders for symbol
    2. Check SL/TP conditions
    3. Close positions if conditions met
    4. Update account balance & trades table
    5. Log to alert history if position closed
  - [ ] Error handling: retry on transient errors; log failures
  - [ ] Type hints everywhere

- [ ] Integrate with `src/ml/signal_generator.py` (optional auto-trading)
  - [ ] Add method `auto_execute_signal(account_id, signal)` in executor
  - [ ] Only execute if `auto_trading_enabled=True` in account preferences

- [ ] Test: `pytest tests/integration/test_workers/test_paper_trading_executor.py -v`

### APScheduler Job
- [ ] Update `src/ml/__main__.py`
  ```python
  executor = PaperTradingExecutor(db, settings)

  # Run every minute on new candles
  scheduler.add_job(
      executor.execute_all_orders,
      "interval",
      minutes=1,
      id="paper_trading_executor",
      max_instances=1,  # Prevent concurrent execution
  )
  ```

### Unit Tests
- [ ] Tests minimum 80% coverage for paper trading module
- [ ] Test scenarios:
  - [ ] Order validation: margin check, leverage check, funds check
  - [ ] Order execution: SL/TP hit, partial position close
  - [ ] Liquidation: margin call triggers closure
  - [ ] P&L calculation: long/short, with/without leverage
  - [ ] Account updates: balance consistency

```bash
pytest tests/unit/test_api/test_paper_trading*.py --cov=src/api/services/paper_trading_service --cov-fail-under=80
```

### Documentation
- [ ] Add docstrings (Google style) to all functions
- [ ] Add example: "How Noah uses paper trading"
  - File: `docs/examples/paper-trading-walkthrough.md`

---

## 2. ALERT SYSTEM

**Équipe Responsable** : Backend (API)

### Database & Migrations
- [ ] Créer migration Alembic pour `alert_rules`, `alert_history`
  - File: `src/etl/migrations/versions/xxx_add_alert_tables.py`

### Pydantic Models
- [ ] Créer `src/shared/models/alerts.py`
  - [ ] `AlertRuleCreate`, `AlertRuleRead`
  - [ ] `AlertHistoryRead`
  - [ ] Validators for `condition` dict
  - [ ] Test: `pytest tests/unit/test_shared/test_alert_models.py`

### ORM Models
- [ ] Update `src/shared/db_models.py`
  - [ ] Add `AlertRuleOrm`, `AlertHistoryOrm`
  - [ ] Add relationships in `UserOrm`

### FastAPI Service
- [ ] Créer `src/api/services/alert_service.py`
  - [ ] `create_rule(user_id, rule_name, rule_type, condition, enabled, channels)`
  - [ ] `get_rules(user_id)` with filtering
  - [ ] `update_rule(rule_id, ...)`
  - [ ] `delete_rule(rule_id)` (soft delete)
  - [ ] `evaluate_rule(rule: AlertRuleOrm, event: dict) -> bool`
  - [ ] `send_alert(user, alert_rule, trigger_event, channels)` → calls email + telegram senders
  - [ ] `log_alert(alert_rule_id, trigger_event, channels, status, error)`
  - [ ] Test: `pytest tests/unit/test_api/test_alert_service.py -v`

### SMTP Sender
- [ ] Créer `src/api/workers/smtp_sender.py`
  ```python
  async def send_email(
      to_address: str,
      subject: str,
      body: str,
      settings: Settings,
  ) -> bool:
      """Send email via SMTP. Return True if success."""
      try:
          async with aiosmtplib.SMTP(hostname=settings.smtp_server, port=settings.smtp_port) as smtp:
              await smtp.login(settings.smtp_user, settings.smtp_password)
              message = EmailMessage()
              message["From"] = settings.smtp_from_address
              message["To"] = to_address
              message["Subject"] = subject
              message.set_content(body)
              await smtp.send_message(message)
              return True
      except Exception as e:
          logger.error("SMTP send failed: %s", e)
          return False
  ```
  - [ ] Dependency: `pip install aiosmtplib`

- [ ] Test: Mock SMTP server (local)
  ```bash
  python -m smtpd -n -c DebuggingServer localhost:1025 &
  pytest tests/unit/test_api/test_smtp_sender.py -v
  ```

### Telegram Bot Sender
- [ ] Créer `src/api/workers/telegram_sender.py`
  ```python
  async def send_telegram_message(
      chat_id: str,
      message: str,
      bot_token: str,
  ) -> bool:
      """Send message to Telegram. Return True if success."""
      url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
      payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

      try:
          async with httpx.AsyncClient() as client:
              resp = await client.post(url, json=payload, timeout=10)
              return resp.status_code == 200
      except Exception as e:
          logger.error("Telegram send failed: %s", e)
          return False
  ```
  - [ ] Store user's Telegram chat_id in `users` table preferences
  - [ ] Test: Mock Telegram API

### Alert Evaluator Worker
- [ ] Créer `src/api/workers/alert_evaluator.py`
  - [ ] Class `AlertEvaluator`
  - [ ] Method: `evaluate_signal_alert(signal: TradingSignal)` → check all rules matching signal
  - [ ] Method: `evaluate_price_alert(symbol, price, price_prev)` → check price change rules
  - [ ] Method: `evaluate_news_alert(article: NewsArticle)` → check keyword rules
  - [ ] Method: `evaluate_portfolio_alert(user_id, position)` → check loss/gain rules
  - [ ] Deduplication: don't send same alert twice in 5 minutes
  - [ ] Type hints + async/await

- [ ] Integrate with signal generator
  - [ ] Hook: when `SignalGenerator.generate()` returns a signal, call `alert_evaluator.evaluate_signal_alert(signal)`
  - [ ] In `src/ml/signal_generator.py` or dedicated callback

- [ ] Test: `pytest tests/integration/test_workers/test_alert_evaluator.py -v`

### FastAPI Router
- [ ] Créer `src/api/routers/alerts.py`
  - [ ] POST `/api/v1/alerts/rules` → create rule
  - [ ] GET `/api/v1/alerts/rules` → list rules (with pagination)
  - [ ] GET `/api/v1/alerts/rules/{rule_id}` → get rule
  - [ ] PUT `/api/v1/alerts/rules/{rule_id}` → update rule
  - [ ] DELETE `/api/v1/alerts/rules/{rule_id}` → delete rule
  - [ ] GET `/api/v1/alerts/history` → list alert history
  - [ ] GET `/api/v1/alerts/my-alerts` → list unread in-app alerts
  - [ ] POST `/api/v1/alerts/read/{alert_id}` → mark alert read
  - [ ] Auth: all endpoints require user context
  - [ ] Error handling: validation errors, missing rule_id, etc.
  - [ ] Test: `pytest tests/integration/test_api/test_alert_endpoints.py -v`

### Configuration Updates
- [ ] Update `src/shared/config.py` with new environment variables
  ```python
  alert_system_enabled: bool = True
  smtp_server: str = "smtp.gmail.com"
  smtp_port: int = 587
  smtp_user: str = ""
  smtp_password: str = ""
  smtp_from_address: str = "alerts@cryptobot.local"
  telegram_bot_token: str = ""
  alert_price_change_threshold: float = 0.10
  alert_portfolio_loss_threshold: float = 0.05
  ```

- [ ] Update `.env.example` with new vars

### Integration with Existing Components
- [ ] Signal router: emit alert_created event after signal save
- [ ] ETL: emit alert_created event for news & regulatory updates

### Unit Tests
- [ ] Tests minimum 80% coverage for alert module
- [ ] Test scenarios:
  - [ ] Rule matching: signal, price, news, portfolio
  - [ ] SMTP send: success, failure, retry
  - [ ] Telegram send: success, failure, invalid token
  - [ ] Deduplication: same rule + same event within 5min → single alert
  - [ ] Alert history: correct logging to database

### Documentation
- [ ] Add docstrings (Google style)
- [ ] Add example: "How Sarah sets up regulatory alerts"

---

## 3. NEW COLLECTORS (Extension ETL)

**Équipe Responsable** : Data Engineering (ETL)

### Database & Migrations
- [ ] Créer migration pour `onchain_metrics`, `regulatory_alerts`
  - [ ] File: `src/etl/migrations/versions/xxx_add_collector_tables.py`
  - [ ] Create indexes on (symbol, metric_type, collected_at) for fast queries

### Pydantic Models
- [ ] Créer `src/shared/models/collectors.py`
  - [ ] `OnChainMetric` model
  - [ ] `RegulatoryAlert` model
  - [ ] Test: `pytest tests/unit/test_shared/test_collector_models.py`

### ORM Models
- [ ] Update `src/shared/db_models.py`
  - [ ] Add `OnChainMetricOrm`, `RegulatoryAlertOrm`

### Etherscan Collector
- [ ] Créer `src/etl/collectors/etherscan_collector.py`
  - [ ] Class `EtherscanCollector`
  - [ ] Methods: `fetch_gas_price()`, `fetch_tx_count()`, `fetch_active_addresses()`
  - [ ] Async/await + error handling (retry with exponential backoff)
  - [ ] Rate limiting: respect free tier (5 calls/sec)
  - [ ] Type hints everywhere
  - [ ] Test: `pytest tests/unit/test_etl/test_etherscan_collector.py -v` (with mocked HTTP)

- [ ] APScheduler job in `src/etl/__main__.py`
  ```python
  scheduler.add_job(
      etherscan_collector.fetch_gas_price,
      "interval",
      minutes=15,
      id="etherscan_gas_price",
  )
  ```

### Blockchain.com Collector
- [ ] Créer `src/etl/collectors/blockchain_collector.py`
  - [ ] Class `BlockchainComCollector`
  - [ ] Methods: `fetch_whale_transactions()`, `fetch_network_metrics()`
  - [ ] Async/await + rate limit handling
  - [ ] Type hints + error handling
  - [ ] Test: Mock HTTP responses

- [ ] APScheduler job

### Regulatory Collector
- [ ] Créer `src/etl/collectors/regulatory_collector.py`
  - [ ] Class `RegulatoryCollector`
  - [ ] Methods: `fetch_esma_alerts()`, `fetch_sec_alerts()`, `fetch_eu_blockchain_news()`
  - [ ] Use `feedparser` library for RSS
  - [ ] Parse impact level from title/content keywords
  - [ ] Deduplication: check if article URL already exists
  - [ ] Type hints + async/await
  - [ ] Test: Mock RSS feeds

- [ ] APScheduler job (daily or 2x/day)

### Generic News Scraper
- [ ] Créer `src/etl/collectors/news_scraper.py`
  - [ ] Class `NewsScraperConfig` (URL, CSS selectors, date format)
  - [ ] Function: `scrape_news(config) -> list[dict]`
  - [ ] Use BeautifulSoup for HTML parsing
  - [ ] Handle date parsing robustly
  - [ ] Deduplication by URL
  - [ ] Type hints
  - [ ] Test: Mock HTML responses

### Phoenix News + Cryptorank
- [ ] Créer `src/etl/collectors/phoenix_news_collector.py`
- [ ] Créer `src/etl/collectors/cryptorank_collector.py`
- [ ] Inherit from generic scraper or use RSS if available

### Loader Integration
- [ ] Update `src/etl/loaders/timescaledb_loader.py`
  - [ ] Add `insert_onchain_metrics(metrics: list[OnChainMetric])`
  - [ ] Add `insert_regulatory_alerts(alerts: list[RegulatoryAlert])`
  - [ ] Batch insert with `executemany`
  - [ ] Handle duplicates (unique constraint on URL for news)

### Unit Tests
- [ ] Tests for each collector (mocked HTTP)
- [ ] Test scenarios:
  - [ ] Successful fetch + parse
  - [ ] Network error → retry
  - [ ] Rate limit → backoff
  - [ ] Invalid response format → log error, skip
  - [ ] Deduplication: same URL twice → insert once

```bash
pytest tests/unit/test_etl/test_*_collector.py --cov=src/etl/collectors --cov-fail-under=80
```

### Documentation
- [ ] Add docstrings to all collectors
- [ ] Add example: "Adding a new news source"

---

## 4. ML PIPELINE EXTENSIONS

**Équipe Responsable** : ML / Data Science

### LSTM Model
- [ ] Créer `src/ml/models/lstm_predictor.py`
  - [ ] Class `LSTMPredictor(nn.Module)`
  - [ ] Constructor: input_size, hidden_size, num_layers, output_size, dropout
  - [ ] Forward pass: (B, seq_len, input_size) → (B, output_size)
  - [ ] Static method: `train_epoch(model, train_loader, optimizer, criterion, device) -> float`
  - [ ] Type hints + docstrings
  - [ ] Test: `pytest tests/unit/test_ml/test_lstm_predictor.py -v`

- [ ] Créer data loader in `src/ml/models/feature_builder.py`
  - [ ] `prepare_lstm_features(ohlcv: pd.DataFrame, indicators: pd.DataFrame) -> torch.Dataset`
  - [ ] Seq length = 60 candles
  - [ ] Features: [open, high, low, close, volume, rsi]
  - [ ] Normalization: StandardScaler per symbol (store metadata as JSON in MinIO)
  - [ ] Test: `pytest tests/unit/test_ml/test_feature_builder_lstm.py`

- [ ] Training script: `src/ml/models/train_lstm.py`
  - [ ] Load data from TimescaleDB
  - [ ] Create train/val/test splits (temporal, no random shuffling)
  - [ ] Walk-forward validation (expanding window)
  - [ ] Log to MLflow: params, metrics, model artifact
  - [ ] Save model to MinIO
  - [ ] Test: `pytest tests/integration/test_ml/test_lstm_training.py`

### Regime Clustering
- [ ] Créer `src/ml/pipelines/regime_clustering.py`
  - [ ] Class `RegimeClusterer`
  - [ ] Constructor: n_regimes=3
  - [ ] Method: `fit(prices: np.ndarray, volumes: np.ndarray) -> RegimeClusterer`
  - [ ] Method: `predict_regime(recent_prices, recent_volumes) -> str`
  - [ ] Features: [price, returns, volume_normalized]
  - [ ] Output: "BULL", "SIDEWAYS", "BEAR"
  - [ ] Type hints + docstrings
  - [ ] Test: `pytest tests/unit/test_ml/test_regime_clustering.py -v`

- [ ] Integration in signal generator
  - [ ] Update `src/ml/signal_generator.py`
  - [ ] Add method: `generate_with_regime(symbol, indicators, regime)`
  - [ ] Adjust confidence ±5% based on regime

### Gymnasium RL Environment
- [ ] Créer `src/ml/environments/trading_env.py`
  - [ ] Class `CryptoPaperTradingEnv(gym.Env)`
  - [ ] Action space: Discrete(3) — HOLD, BUY, SELL
  - [ ] Observation space: Box(6,) — [price, rsi, bb_upper, bb_lower, balance, position]
  - [ ] Methods: `reset()`, `step(action)`, `_get_observation()`
  - [ ] Reward: realized PnL - fees
  - [ ] Episode length: 252 candles (1 year of daily data)
  - [ ] Type hints + docstrings
  - [ ] Test: `pytest tests/unit/test_ml/test_trading_env.py -v`

### Configuration
- [ ] Update `src/shared/config.py`
  ```python
  ml_lstm_enabled: bool = True
  ml_rl_env_enabled: bool = False  # Optional for Phase 2+
  ml_regime_clustering_enabled: bool = True
  ml_regime_update_frequency_minutes: int = 60
  ```

### MLflow Integration
- [ ] Update `src/ml/mlflow_utils.py` to log LSTM + regime experiments
  - [ ] Log hyperparams: seq_len, hidden_size, num_layers, dropout, learning_rate
  - [ ] Log metrics: train_loss, val_loss, test_accuracy, Sharpe ratio
  - [ ] Log artifacts: trained model (PyTorch checkpoint), metadata as JSON

### Unit Tests
- [ ] Tests minimum 80% coverage for ML extensions
- [ ] Test scenarios:
  - [ ] LSTM forward pass: shape consistency
  - [ ] Feature builder: correct scaling, no NaN
  - [ ] Regime clustering: convergence, stable predictions
  - [ ] RL environment: reset, step, done conditions
  - [ ] MLflow logging: experiments created, artifacts saved

```bash
pytest tests/unit/test_ml/test_lstm*.py tests/unit/test_ml/test_regime*.py --cov=src/ml --cov-fail-under=80
```

### Documentation
- [ ] Add docstrings (Google style)
- [ ] Add example: "How to train LSTM on 1h candles"
- [ ] Add RL environment usage example

---

## Integration Checklist

### Shared Models & Config
- [ ] All new models exported in `src/shared/models/__init__.py`
- [ ] All new ORM classes exported in `src/shared/db_models.py`
- [ ] Config class updated with all new env vars
- [ ] `.env.example` updated with descriptions

### Database Migrations
- [ ] All migrations numbered sequentially
- [ ] Test migrations in order: `alembic upgrade head`
- [ ] Verify schema matches ORM definitions

### API Integration
- [ ] All routers registered in `src/api/main.py`
- [ ] CORS updated if new routes need cross-origin access
- [ ] Rate limiting on sensitive endpoints (auth, alerts)

### Worker Integration
- [ ] All new workers added to `src/ml/__main__.py` or separate worker image
- [ ] APScheduler jobs configured
- [ ] Health checks for workers in docker-compose
- [ ] Logging configured (log level, format)

### Docker & CI/CD
- [ ] Update `docker-compose.yml` with new services (if any)
- [ ] Update GitHub Actions workflows (lint, type check, test)
- [ ] Ensure all tests pass before merge

### Documentation
- [ ] Update `docs/00-overview.md` to mention new components
- [ ] Add new team docs if needed (e.g., `docs/07-collectors.md`)
- [ ] Update README with new features

---

## Cross-Team Dependencies

| Component | Data Eng | ML | Backend | Frontend | DevOps |
|-----------|----------|----|---------|---------|----|
| Paper Trading | Schema | - | Service + Router + Worker | Pages | Docker |
| Alert System | Schema | - | Service + Router + Worker | Pages | Docker |
| New Collectors | Collectors + Loaders | - | - | Dashboard | Docker |
| ML Extensions | - | Models + Env + Training | Signal integration | - | MLflow |

**Critical Sync Points** :
1. **Week 1-2**: Finalize all database schemas (Data Eng → All)
2. **Week 3**: All Pydantic models defined (Shared → All)
3. **Week 4-5**: Integration between components (cross-team)
4. **Week 6**: Full system integration test

---

## Quality Gates (MUST pass before merge to main)

```bash
# Linting
ruff check src/ --fix && ruff format src/

# Type checking
mypy src/ --strict

# Tests
pytest tests/unit tests/integration --cov=src --cov-fail-under=80

# Docker build
docker-compose build

# Manual testing
# 1. Create paper account, place order, verify execution
# 2. Create alert rule, trigger alert, verify SMTP/Telegram delivery
# 3. Run a new collector, verify data in database
# 4. Train LSTM, verify MLflow logs
```

---

## Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Paper Trading** | 2 weeks | Accounts, orders, executor, 80%+ tests |
| **Phase 2: Alert System** | 2 weeks | Rules, senders, evaluator, 80%+ tests |
| **Phase 3: New Collectors** | 2 weeks | Etherscan, Blockchain, Regulatory, News |
| **Phase 4: ML Extensions** | 2 weeks | LSTM, Clustering, RL environment |
| **Integration & QA** | 1 week | Full system test, documentation, polish |
| **Total** | **9 weeks** | Production-ready new components |

---

## Sign-Off

- [ ] Data Engineering Lead: Approve database schema & migrations
- [ ] ML Lead: Approve model architecture & training pipeline
- [ ] Backend Lead: Approve API design & integration
- [ ] Frontend Lead: Approve UI/UX for new features
- [ ] DevOps Lead: Approve Docker & CI/CD updates
- [ ] Project Manager: Confirm timeline & dependencies
