# Architectural Decision Records (ADRs) — Nouveaux Composants

---

## ADR-001: Paper Trading Backend Architecture

**Status**: Proposed

**Context**:
Noah wants to simulate trading on generated signals without real funds. Options:
1. **Option A** (Selected): Store trades in TimescaleDB, execute synchronously on new candles, no separate message broker
2. **Option B**: Use Redis + async message queue (RabbitMQ/Kafka), decouple order creation from execution
3. **Option C**: Use blockchain smart contract (Solana/Ethereum) for on-chain simulation (over-engineering for V1)

**Decision**:
Use **Option A** — TimescaleDB storage with synchronous execution in ml-worker.

**Rationale**:
- **Simplicity**: No external broker adds ~2 weeks of setup/ops work
- **Consistency**: All state in one database = easier debugging
- **Scalability**: 100 accounts × 50 positions = 5k checks/minute is acceptable in Python asyncio
- **Maintainability**: Clear execution flow: new candle → check orders → update DB
- **Cost**: Zero additional infrastructure

**Trade-offs**:
- **Rejected**: Message queue would improve decoupling but adds operational complexity for school project
- **Accepted**: Synchronous execution means 1-5 min delay vs real-time (acceptable for simulation)

**Consequences**:
- Paper trading executor runs in ml-worker container (APScheduler job)
- All order state in PostgreSQL with strong ACID guarantees
- No order queue persistence needed (orders are DB records)

**ADR-001 Success Metrics**:
- [ ] Executor processes all open orders within 60 seconds of new candle
- [ ] No lost orders or incorrect balance calculations (audit via test suite)
- [ ] SL/TP execution accuracy > 99%

---

## ADR-002: Alert System Delivery Channels

**Status**: Proposed

**Context**:
Three personas need alerts via different channels:
- Noah (trader): Telegram for instant mobile notifications
- Sarah (journalist): Email for important regulatory alerts
- Aleksandar (investor): In-app dashboard or email summaries

Options:
1. **Option A** (Selected): Email (SMTP) + Telegram (bot API) + in-app (polling), all optional based on config
2. **Option B**: Use managed service (SendGrid, Twilio) for emails + SMS
3. **Option C**: WebSocket push (real-time in-app) for all alerts
4. **Option D**: Slack integration only

**Decision**:
Use **Option A** — SMTP + Telegram Bot API + in-app polling.

**Rationale**:
- **Zero cost**: SMTP via Gmail app password (free), Telegram bot API (free), no external subscriptions
- **Flexibility**: Each user chooses channels (email, Telegram, in-app)
- **Decoupling**: Optional channels → graceful degradation if email fails
- **School project**: No budget for SendGrid/Twilio

**Trade-offs**:
- **Rejected Option B**: Would require credit card + adds vendor lock-in
- **Rejected Option C**: WebSocket adds complexity; polling is simpler + sufficient for V1
- **Accepted**: In-app polling (vs push) slightly increases client-side load but vastly simpler backend

**Consequences**:
- SMTP config via `.env` (Gmail, SendGrid if user has account)
- Telegram bot token optional (leave empty to disable)
- In-app alerts stored in `alert_history` table, client polls `/api/v1/alerts/my-alerts`
- Failed deliveries logged but don't block other channels

**ADR-002 Success Metrics**:
- [ ] Email delivery success rate > 95% (tested with mock SMTP)
- [ ] Telegram delivery success rate > 95% (mocked)
- [ ] In-app alerts appear within 5 seconds of rule trigger
- [ ] No duplicate alerts (5-min deduplication window)

---

## ADR-003: New Collectors — Free Data Only, No Aggregators

**Status**: Proposed

**Context**:
Sarah wants regulatory data + on-chain metrics. Options:
1. **Option A** (Selected): Free public APIs (Etherscan, Blockchain.com, ESMA RSS) + BeautifulSoup scraping
2. **Option B**: Use paid aggregator (Glassnode, CryptoQuant, Messari) for all metrics
3. **Option C**: Self-hosted blockchain node (full BTC/ETH node) to derive metrics

**Decision**:
Use **Option A** — Free tier APIs + RSS + web scraping.

**Rationale**:
- **Cost**: Zero budget impact; no paid subscriptions
- **Availability**: Etherscan/Blockchain.com free tiers have rate limits but sufficient for V1 (1 symbol per 30 sec)
- **Maintainability**: Simple HTTP client + parsing, no SDK dependencies
- **Regulatory**: ESMA/SEC publish RSS freely; no scraping of protected content

**Trade-offs**:
- **Rejected Option B**: Glassnode ~$300/month = out of scope for school project
- **Rejected Option C**: Blockchain node requires ~200GB disk + 24/7 uptime; too much ops overhead
- **Accepted**: Rate limits mean we can't update all symbols every minute (30s minimum interval)

**Consequences**:
- Etherscan/Blockchain.com collectors with exponential backoff on 429 errors
- On-chain metrics updated every 15-30 min (not real-time)
- ESMA/SEC regulatory data updated daily
- News scraped hourly (depends on source)

**ADR-003 Success Metrics**:
- [ ] Etherscan gas price collected every 15 min for all 9 weeks
- [ ] No repeated 429 errors (exponential backoff working)
- [ ] Blockchain.com whale alerts updated every 30 min
- [ ] ESMA alerts collected daily with >90% uptime

---

## ADR-004: ML Extensions — Phase 2 Foundation, Phase 1 Optional RL

**Status**: Proposed

**Context**:
Phase 1 = rules engine. Phase 2 = supervised learning. RL is nice-to-have. Options:
1. **Option A** (Selected): LSTM for next-step prediction + K-means for regime clustering; RL deferred to Phase 3
2. **Option B**: RL (DQN/PPO) now, skipping LSTM
3. **Option C**: Both LSTM + RL in same phase (overambitious)
4. **Option D**: Only clustering, no LSTM

**Decision**:
Use **Option A** — LSTM + clustering in Phase 2; RL as optional Phase 3+.

**Rationale**:
- **Scope**: LSTM + clustering are proven, well-tested techniques; RL is research-level for trading
- **Data**: Only 2-3 months of historical data available; RL typically needs 1+ year for convergence
- **Team capability**: LSTM/clustering have clear metrics (Sharpe, win rate); RL is harder to debug
- **Phasing**: Separate concerns into phases; RL can plug into signal generator later

**Trade-offs**:
- **Rejected Option B**: RL without LSTM leaves money on table (signal quality)
- **Rejected Option C**: Too many moving parts; would miss end date
- **Accepted**: RL deferred (can add Gymnasium env in Phase 3 without breaking Phase 2)

**Consequences**:
- LSTM trained on expanded feature set (OHLCV + RSI + Bollinger + harmonic)
- Models logged to MLflow with walk-forward backtesting
- Regime clustering runs daily, updates signal confidence
- RL environment created but not integrated (env is standalone, can test offline)

**ADR-004 Success Metrics**:
- [ ] LSTM Sharpe ratio > 0.5 on test set (walk-forward)
- [ ] Regime clustering converges in <100 iterations (K-means)
- [ ] Signal confidence adjustment from clustering: ±5% cap, no crashes
- [ ] RL environment steps without errors (validation, not training)

---

## ADR-005: Alert Deduplication — 5-Minute Window, Per-Rule

**Status**: Proposed

**Context**:
Same rule (e.g., "BUY signal on BTCUSDT") might trigger every minute. Spam risk. Options:
1. **Option A** (Selected): Deduplicate per (rule_id, trigger_event_hash) within 5 minutes
2. **Option B**: Deduplicate per user globally (1 alert per 5 min)
3. **Option C**: No deduplication; user controls via rule frequency
4. **Option D**: Deduplicate per symbol (not per rule)

**Decision**:
Use **Option A** — Per-rule deduplication with 5-min window.

**Rationale**:
- **Balance**: Prevents spam (same rule firing repeatedly) while allowing different rules to trigger in same window
- **User control**: Different rules can have independent schedules
- **Example**: Rule "BUY BTCUSDT" fires at 10:00 → suppressed until 10:05; Rule "SELL ETHUSD" can fire at 10:02 independently
- **Implementation**: Hash(rule_id, trigger_event) + timestamp in memory cache (Redis-light)

**Trade-offs**:
- **Rejected Option B**: Too aggressive; miss important alerts from different rules
- **Rejected Option C**: Puts burden on user to configure frequency
- **Accepted**: Need simple in-memory cache (dict or lru_cache)

**Consequences**:
- Alert evaluator maintains `dedup_cache: dict[str, datetime]` keyed by (rule_id, event_hash)
- Cache cleaned every 5 min (pruning old entries)
- If duplicate detected, log to `alert_history` with `status="DEDUPED"` (audit trail)

**ADR-005 Success Metrics**:
- [ ] Same rule firing 10x in 1 min → only 1 alert sent
- [ ] 2 different rules firing in same min → 2 alerts sent
- [ ] Dedup cache max size < 1000 entries (memory safe)

---

## ADR-006: Paper Trading Leverage — Max 10x, Min Margin 2x

**Status**: Proposed

**Context**:
Paper trading should be realistic but not reckless. Noah sometimes trades with leverage. Options:
1. **Option A** (Selected): Max leverage 10x, required margin = 2x notional
2. **Option B**: Max 20x (like FTX/Hyperliquid limits)
3. **Option C**: No leverage (1x only)
4. **Option D**: Dynamic leverage based on volatility

**Decision**:
Use **Option A** — 10x max leverage, 2x margin requirement.

**Rationale**:
- **Risk management**: 10x leverage is aggressive enough to test signals while preventing ruin
- **Realism**: Binance futures allows up to 125x but most traders use <10x
- **Margin safety**: 2x requirement means account needs 50% capital vs position notional (industry standard)
- **Simplicity**: Fixed limits, no dynamic calculations needed

**Trade-offs**:
- **Rejected Option B**: 20x+ is too aggressive for a school project; invites "blowing up" scenarios
- **Rejected Option C**: 1x only makes leverage ineffective for realistic trading sim
- **Accepted**: Fixed limits are simpler than dynamic (no volatility dependency)

**Consequences**:
- Paper order validation: `if leverage > leverage_max → reject order`
- Margin calc: `margin_required = notional / leverage * 2.0`
- Liquidation: if `balance < margin_required on any position → force close`

**ADR-006 Success Metrics**:
- [ ] Orders with leverage > 10x rejected with 422 error
- [ ] Liquidation triggers when balance < margin_required (tested)
- [ ] Margin calculation matches Binance formula (audited via spreadsheet)

---

## ADR-007: Database Schema — All in TimescaleDB, No Separate Caches

**Status**: Proposed

**Context**:
New components need storage. Options:
1. **Option A** (Selected): All tables in PostgreSQL + TimescaleDB, use indexes for speed
2. **Option B**: Redis cache layer for hot data (paper_accounts, alert_rules)
3. **Option C**: MongoDB for flexible schemas (alerts, onchain_metrics)
4. **Option D**: Separate database per component (microservices-lite)

**Decision**:
Use **Option A** — PostgreSQL + TimescaleDB only.

**Rationale**:
- **Operational simplicity**: Single database = single backup, single connection pool
- **Consistency**: ACID transactions for critical updates (balance, order state)
- **Indexes**: Modern PostgreSQL indexes (B-tree, GIN on JSONB) are fast enough
- **No vendor lock-in**: TimescaleDB is PostgreSQL-compatible
- **Team familiarity**: Data eng already knows PostgreSQL

**Trade-offs**:
- **Rejected Option B**: Redis adds ops burden (replication, persistence, monitoring)
- **Rejected Option C**: MongoDB schema drift risk; transaction support weaker
- **Rejected Option D**: Polyglot database is overengineering for school project
- **Accepted**: May need connection pooling (PgBouncer) if load grows

**Consequences**:
- All tables in single `cryptobot` database
- Composite indexes on (user_id, symbol), (symbol, timestamp), (status)
- Batch operations use `INSERT ... ON CONFLICT` for deduplication
- Connection pool via SQLAlchemy asyncio

**ADR-007 Success Metrics**:
- [ ] Paper order lookup by (account_id, symbol) < 10ms
- [ ] Alert rule lookup by (user_id, enabled) < 10ms
- [ ] Full system fits in single DB (no replication complexity)

---

## ADR-008: Frontend Integration — Streamlit Multi-Page, No New Framework

**Status**: Proposed

**Context**:
New features (paper trading, alerts) need UI. Options:
1. **Option A** (Selected): Add pages to existing Streamlit app (pages/paper_trading.py, pages/alerts.py)
2. **Option B**: Build React SPA for new features only
3. **Option C**: Use Dash instead (too late, already Streamlit)
4. **Option D**: No UI for now, API-only

**Decision**:
Use **Option A** — Extend Streamlit multi-page architecture.

**Rationale**:
- **Consistency**: All features in one UI framework; single look/feel
- **Speed**: Streamlit dev is 2-3x faster than React for data apps
- **Team constraint**: No frontend team with React expertise
- **Scope**: Paper trading + alerts are table-heavy UI (Streamlit strength)

**Trade-offs**:
- **Rejected Option B**: React would be overkill + 2+ weeks lost to setup
- **Rejected Option D**: API-only leaves users navigating raw JSON (poor UX)
- **Accepted**: Streamlit less customizable than React but sufficient for V1

**Consequences**:
- New pages: `src/frontend/pages/02_Paper_Trading.py`, `src/frontend/pages/05_Alerts.py`
- Reuse existing `api_client.py` for all HTTP calls
- Charts: Plotly for equity curve, Streamlit tables for orders/history
- Auth: Existing JWT token flow (no changes needed)

**ADR-008 Success Metrics**:
- [ ] Paper trading page loads in <2 sec
- [ ] Alert rules CRUD functional (create, list, edit, delete)
- [ ] Charts render correctly on all browsers
- [ ] Mobile responsive (Streamlit default)

---

## ADR-009: Testing Strategy — 80% Unit, 15% Integration, 5% E2E

**Status**: Proposed

**Context**:
New code needs tests. Allocation of effort options:
1. **Option A** (Selected): 80% unit (mocked), 15% integration (Docker services), 5% E2E (full stack)
2. **Option B**: 50% unit, 30% integration, 20% E2E (slower feedback loop)
3. **Option C**: 100% E2E (slow but thorough)
4. **Option D**: No integration tests (fast but risky)

**Decision**:
Use **Option A** — 80/15/5 split with pytest + respx/mocking.

**Rationale**:
- **Speed**: Unit tests run in <5 sec; integration in <30 sec; E2E in <2 min
- **Feedback**: Fast tests encourage TDD; slow tests discourage iteration
- **Reliability**: Mocked tests deterministic; E2E brittle (timing, external deps)
- **Cost/value**: 80% unit catches most bugs; 15% integration catches wiring issues

**Trade-offs**:
- **Rejected Option B**: 50% unit too few; miss edge cases caught by isolated logic tests
- **Rejected Option C**: E2E only would require 20+ min test runs; too slow for tight feedback loop
- **Accepted**: May need a few E2E tests for critical paths (signal → alert → notification)

**Consequences**:
- Unit tests: `tests/unit/test_api/`, `tests/unit/test_ml/`, `tests/unit/test_etl/`
- Integration tests: `tests/integration/` require Docker Compose running
- E2E tests: `tests/e2e/` test Noah's complete flow (signal → paper trade → alert)
- CI/CD: Unit tests on every commit; integration + E2E on PR

**ADR-009 Success Metrics**:
- [ ] Unit test coverage > 80% for all modules
- [ ] `pytest tests/unit/ -x` completes in <10 sec
- [ ] `pytest tests/integration/ -x` completes in <60 sec
- [ ] All E2E tests green on merge to main

---

## ADR-010: Documentation — Markdown + Docstrings, No Confluence

**Status**: Proposed

**Context**:
How to document new components? Options:
1. **Option A** (Selected): Markdown files in `docs/`, Google-style docstrings in code
2. **Option B**: Confluence wiki (central, but requires license)
3. **Option C**: README only (minimal)
4. **Option D**: Auto-generated docs from OpenAPI schema (API only)

**Decision**:
Use **Option A** — Markdown + code docstrings.

**Rationale**:
- **Free**: No Confluence license needed
- **Version control**: Docs in git = same review process as code
- **Sync**: Code and docs stay in sync (both change in same PR)
- **Searchable**: GitHub search works on Markdown
- **Portable**: Can render as HTML via mkdocs or GitHub pages

**Trade-offs**:
- **Rejected Option B**: Confluence sync is manual; goes out of date
- **Rejected Option C**: README only misses important design rationale
- **Accepted**: Google-style docstrings are longer than one-liners but more readable

**Consequences**:
- Architecture doc: `.claude/specs/new-components/02-system-architecture.md` (this file)
- Implementation checklist: `.claude/specs/new-components/IMPLEMENTATION_CHECKLIST.md`
- ADRs: `.claude/specs/new-components/ADRs.md` (this file)
- Code: Every function/class has docstring with Args, Returns, Raises
- Examples: `docs/examples/paper-trading-walkthrough.md`, etc.

**ADR-010 Success Metrics**:
- [ ] Every public function has docstring (enforced by mypy)
- [ ] Architecture doc updated when design changes
- [ ] No stale Markdown (auto-checked via link-checker in CI)

---

## Appendix: Decision Log

| ADR | Title | Status | Owner | Date |
|-----|-------|--------|-------|------|
| 001 | Paper Trading Backend | Proposed | Backend | 2026-03-14 |
| 002 | Alert Delivery Channels | Proposed | Backend | 2026-03-14 |
| 003 | New Collectors — Free Data | Proposed | Data Eng | 2026-03-14 |
| 004 | ML Extensions Phasing | Proposed | ML | 2026-03-14 |
| 005 | Alert Deduplication | Proposed | Backend | 2026-03-14 |
| 006 | Paper Trading Leverage | Proposed | Backend | 2026-03-14 |
| 007 | Database Schema — Single DB | Proposed | Data Eng | 2026-03-14 |
| 008 | Frontend — Streamlit Multi-Page | Proposed | Frontend | 2026-03-14 |
| 009 | Testing 80/15/5 Split | Proposed | QA | 2026-03-14 |
| 010 | Documentation Strategy | Proposed | Team | 2026-03-14 |

---

## How to Update ADRs

1. When a design decision needs reconsideration, open an issue referencing the ADR
2. Propose a new ADR with Status=Proposed, list Context/Options/Decision
3. Get team sign-off (Product, Architecture, affected teams)
4. Update Status=Accepted and add Date
5. If rejected, update Status=Superseded and link to replacement ADR

Example:
```markdown
## ADR-999: Replace X with Y

**Status**: Superseded by ADR-1000 (2026-04-01)

**Reason**: Y proved faster in benchmarks; X had maintenance burden.
```
