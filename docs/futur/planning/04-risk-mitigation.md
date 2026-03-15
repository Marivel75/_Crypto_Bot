# Risk Mitigation & Contingency Plan

---

## Risk Registry (Comprehensive)

### Critical Risks (High Impact, High Probability)

#### R1: RL Training Convergence Failure

**Description**: Agents RL (DQN/PPO) ne convergent pas, loss reste haut, reward ne monte pas.

**Impact**: F8 incomplète, MVP incomplet, soutenance compromise.

**Probability**: MEDIUM-HIGH (60%) — Deep RL est complexe, hyperparameters sensibles.

**Mitigations**:
1. **Commencer tôt S15** — Laisser tourner 48h+ en parallèle
2. **Simplify first** — 1 agent (DQN) au lieu de 2 (DQN+PPO)
3. **Reduce action space** — BUY/HOLD only, no SELL (plus simple)
4. **Baseline metric** — Random agent comme comparaison (pas de loss, seulement reward)
5. **Early stopping** — Si pas converged S15-week2, pivot Plan B (F8 scope cut)

**Owner**: Mikael

**Trigger**: Loss flat après 50k steps OU reward plateau <0.1

**Contingency**: Plan B-1 (DQN only, reduced scope) → faisable S15-S16

---

#### R2: Paper Trading Model Complexity

**Description**: Logique clôture (SL/TP/timeout), calcul PnL, edge cases (long/short) = complex, bugs cachés.

**Impact**: F7 retardée 1-2 sprints, F8 bloquée.

**Probability**: MEDIUM (50%) — Beaucoup de logique métier à tester.

**Mitigations**:
1. **Simplify first pass** — Clôture sur SL/TP uniquement (drop timeout)
2. **Exhaustive unit tests** — 50+ test cases (long/short, partial fill, SL/TP simultané)
3. **Mock PnL calculation** — Vérifier formules sur papier avant code
4. **Pair programming S13** — Jules + Mikael sur model design
5. **E2E test avant S14** — 1-2 trades réelles en staging

**Owner**: Mikael (model) + Jules (API integration)

**Trigger**: F7 slip >3 days OU bugs trouvés après S13 merge

**Contingency**: Déplacer testing vers S14, raccourcir S12 (F5 deprioritize)

---

#### R3: LSTM Overtraining / Underfitting

**Description**: Modèle LSTM accuracy <65%, F1 <0.60, données insuffisantes.

**Impact**: F6 incomplète, signal predictor qualité réduite, démo faible.

**Probability**: MEDIUM (40%) — Données historiques peuvent être limitées.

**Mitigations**:
1. **Check data first** — S13-week1: valider ≥100k samples disponibles
2. **Baseline model** — Random Forest simple en parallèle (fallback)
3. **Feature engineering** — RSI/Bollinger/volume normalisés correctement
4. **Regularization** — Dropout, L2 penalty pour éviter overfit
5. **Walk-forward CV** — Validation temporelle (pas random split)

**Owner**: Mikael

**Trigger**: Accuracy <65% après 20 epochs OU validation gap >10%

**Contingency**: Réduire scope (3-layer LSTM → 2-layer) OU drop F6 de MVP

---

### High Impact Risks

#### R4: API Integration Delays

**Description**: F7.2 (Paper Trading API) bloquée par dépendances, schema changes.

**Impact**: F7.3 & F8 retardées, integration complexity.

**Probability**: MEDIUM (40%) — Dépendances cross-team.

**Mitigations**:
1. **API design S13-week1** — Figeler schema avant implémentation
2. **Mock API first** — Jules mock endpoints pour Mikael test F7.3 in parallel
3. **Minimal dependencies** — Signal + portfolio = only 2 new tables
4. **Contract testing** — Swagger schema versioned, backwards compatible

**Owner**: Jules (API), Mikael (consumer)

**Trigger**: F7.2 slip >2 days

**Contingency**: Utiliser Pydantic models mock, intégration retardée S14

---

#### R5: Data Quality / Collection Failures

**Description**: OHLCV data gaps, Blockchain.com API down, news scraper broken.

**Impact**: ML model training fails, signals generées incorrectes, outage.

**Probability**: LOW-MEDIUM (30%) — Already have backups (Binance, CoinGecko).

**Mitigations**:
1. **Monitoring** — APScheduler logs toutes collectes, alertes sur gap >1h
2. **Fallbacks** — Blockchain.com down? Use cache local + retry
3. **Validation** — Pydantic checks OHLCV cohérence (open/close, volume ≥0)
4. **Data warehouse** — Données toujours sauvegardées MinIO, restore possible
5. **Graceful degradation** — Signals work sans on-chain data (F5 optional)

**Owner**: Jules (ETL)

**Trigger**: Data gap >4h OU validation failures >5% records

**Contingency**: Fallback à données statiques, délay F5 on-chain

---

### Medium Impact Risks

#### R6: Performance / Scaling Issues

**Description**: API lent (>1s latence), Streamlit lag, queries slow.

**Impact**: Démo faible, soutenance problématique.

**Probability**: LOW-MEDIUM (25%) — Not optimized yet.

**Mitigations**:
1. **Profile early** — S14: run load test (100 req/s)
2. **Index critical columns** — TimescaleDB: symbol, timestamp indexes
3. **Pagination** — API returns max 100 trades per request
4. **Streamlit cache** — st.cache_data on expensive queries (TTL=5min)
5. **Async API** — FastAPI async/await pour I/O

**Owner**: Jules (API) + Mikael (ML queries)

**Trigger**: P99 latency >500ms OU Streamlit timeout

**Contingency**: Optimize later (S16), reduce feature scope

---

#### R7: Regex/Parsing Fragility (Scraper)

**Description**: BeautifulSoup scraper breaks si HTML structure change.

**Impact**: F1 unreliable, regulatory data missing.

**Probability**: MEDIUM (50%) — Websites update HTML.

**Mitigations**:
1. **Robust CSS selectors** — Use class/id, not tag hierarchy
2. **Fallback extraction** — Multiple selector attempts, log failures
3. **Version control HTML** — Git store example HTMLs (test fixtures)
4. **Monitoring** — Alert if parse success < 95%
5. **Manual fallback** — Dashboard to show "last successful parse"

**Owner**: Jules

**Trigger**: Parse success <90% on 2 sources

**Contingency**: Drop F1 (keep F2 RSS only)

---

#### R8: Testing/Coverage Lag

**Description**: Coverage <80%, untested edge cases, bugs slip to prod.

**Impact**: Quality degrade, bugs in soutenance.

**Probability**: MEDIUM (35%) — Pressure to ship fast.

**Mitigations**:
1. **TDD discipline** — Write tests before code, non-negotiable
2. **Coverage gate CI** — Fail build if <80%, enforce locally
3. **Code review** — Check coverage per MR
4. **Test fixtures** — Maintain shared test data (JSON, CSV)
5. **Pair testing** — Jules review Mikael's tests, vice-versa

**Owner**: Both (shared responsibility)

**Trigger**: Coverage trend ↓ 2 sprints ORnew code <75%

**Contingency**: Extend S16 for test hardening

---

### Lower Probability Risks

#### R9: Team Availability / Illness

**Description**: Jules ou Mikael indisponible 1-2 semaines.

**Impact**: Dépendances bloquées, délai cascade.

**Probability**: LOW (15%) — Young team, project school (not 24/7).

**Mitigations**:
1. **Documentation** — Code & design well-documented for handoff
2. **Cross-training** — Jules learns Mikael's ML basics, vice-versa
3. **Async work** — Async communication (no real-time dependency)
4. **Scope protection** — Keep current sprint focused (no long-tail tasks)

**Owner**: Team leads

**Trigger**: Absence >3 consecutive days

**Contingency**: Reduce current sprint scope, extend timeline 1 week

---

#### R10: Infrastructure Outage (Docker/DB/MinIO)

**Description**: Docker Compose fails, TimescaleDB corruption, MinIO unavailable.

**Impact**: Cannot develop/deploy, full stop.

**Probability**: LOW (10%) — Docker Compose stable locally.

**Mitigations**:
1. **Daily backup** — pg_dump to MinIO (automatic)
2. **Test restore** — Monthly restore test (documented)
3. **Dev env isolation** — Each dev has local Docker Compose
4. **Snapshots** — Git commits serve as fallback (code only)

**Owner**: DevOps (if applicable)

**Trigger**: Infrastructure down >2 hours

**Contingency**: Develop offline, merge when back up

---

## Risk Severity Matrix

```
                  Probability
                H        M        L
I               ────────────────────
m    H  │ R1    │ R2, R3  │ R9, R10 │
p      │ (RL)  │ (Model) │         │
a      ├────────┼─────────┼─────────┤
c    M  │ R4, R5 │ R6, R7, R8│      │
t      │        │ (Perf,  │        │
       │        │  Parse) │        │
       ├────────┼─────────┼─────────┤
       L  │        │        │ (Plan B) │
         └────────┴─────────┴─────────┘
```

**Quadrant 1 (Top-Left)**: R1 = CRITICAL, escalate daily

**Quadrant 2 (Top-Middle)**: R2, R3 = HIGH, monitor weekly

**Quadrant 3 (Bottom-Left/Middle)**: R4-R8 = MEDIUM, monitor bi-weekly

**Quadrant 4 (Bottom-Right)**: R9, R10 = LOW, document contingency only

---

## Weekly Risk Review

**Every Friday 16:30** (after sprint review):

```
Attendees: Jules, Mikael

Agenda:
1. Update risk status (Probability/Impact/Trigger)
   - R1 RL convergence: STILL HIGH (50%)
   - R2 Model complexity: RESOLVED (unit tests complete)
   - R7 Parser fragility: UP (website changed) → now HIGH

2. New risks identified?
   - R11: Soutenance date change? (assume NO, fixed)
   - R12: Team availability? (assume OK)

3. Mitigation actions taken
   - [ ] Mikael: Started RL training early
   - [ ] Jules: Added HTML fixtures for scraper

4. Escalations needed?
   - If R1 not converging by S15-week2 → activate Plan B
   - If R2 model bugs >5 → pair program
```

---

## Plan B Decision Tree

```
START (S11-S12 normal path)
    │
    ├─→ S13: Is F7.1 model done on-time?
    │   ├─YES → continue S14 F7.2/F7.3 normal
    │   └─NO → SLIP detected
    │       └─→ Is slip <3 days?
    │           ├─YES → extend S13, continue
    │           └─NO → Activate Plan B-1 (LSTM reduction)
    │
    ├─→ S15: Is F7 (paper trading) done?
    │   ├─YES → continue S15 F8 normal
    │   └─NO → CRITICAL, activate Plan B-2 (F8 scope cut)
    │
    └─→ S15-Mid: Are RL agents converging?
        ├─YES → continue S16 validation
        └─NO → Activate Plan B-1 (DQN only)
            └─→ Is DQN converging S16-week1?
                ├─YES → submit DQN + note PPO future work
                └─NO → Activate Plan B-2 (RL removed entirely)
```

---

## Plan B Options (Detailed)

### Plan B-0: Add Buffer Sprint (Escape Hatch)

**Trigger**: Multiple high-risk items materialized, time critical.

**Action**:
- Add S17 (2 weeks) extending soutenance to late June
- Risk: Might not be possible (admin constraint)
- Probability: LOW (only if Uni allows)

**Impact**: Resolves all risks, low pressure.

---

### Plan B-1a: LSTM Scope Reduction

**Features to cut**:
- LSTM from 2 layers → 1 layer
- Training steps: 100k → 50k
- Hyperparameter grid: full → 4 params only
- Validation: walk-forward → simple split ok

**Time saved**: ~8 hours (50% of F6)

**Impact**: Model quality reduced, accuracy may drop <65%, acceptable for school project.

**When to trigger**: If F6 slow or S13 overload confirmed.

---

### Plan B-1b: RL Scope Reduction

**Features to cut**:
- Keep DQN only (drop PPO)
- Action space: BUY/SELL/HOLD → BUY/HOLD only
- Training steps: 100k → 50k
- Environment: simplified reward (PnL only, no transaction cost)

**Time saved**: ~10 hours (45% of F8)

**Impact**: Less sophisticated agent, but still demonstrates RL. Dedup: "Phase 1 DQN ready, PPO future work".

**When to trigger**: If S15 RL agents not converging by mid-week.

---

### Plan B-1c: Combined Reductions (LSTM + RL)

Apply B-1a + B-1b together.

**Time saved**: ~18 hours (20% project)

**Risk level**: LOW (both still deliver value)

**Go-live**: S16 with confidence.

---

### Plan B-2a: F5 (On-Chain) Cut

**Scope**: Remove Blockchain.com data collection entirely.

**Time saved**: 5 hours (F5 = 5 points)

**Impact**: MarketData less rich, but signals still work. Dedup: "On-chain metrics future phase."

**When to trigger**: S12 if F4 (Alerts) overrun.

---

### Plan B-2b: F3 (KMeans) Cut

**Scope**: Remove clustering analysis entirely.

**Time saved**: 3 hours (F3 = 3 points)

**Impact**: No cluster dashboard, but not critical for trading. Dedup: "Exploratory analytics S2."

**When to trigger**: S11 if Mikael overloaded, move to S14 if buffer exists.

---

### Plan B-2c: F8 (RL) Cut

**Scope**: Remove RL agents entirely, keep paper trading + LSTM.

**Time saved**: 21 hours (F8 = 21 points)

**Impact**: MVP is complete (signals + simulation + LSTM), RL is "future work".

**When to trigger**: S16-week1 if RL agents non-functional.

**Dedup**:
```
"We delivered Phase 1 (rule engine) + Phase 2-lite (LSTM + paper trading).
RL agents are designed and architectured, implementation pushed to Phase 2."
```

---

## Contingency Allocation (Time Buffer)

**Total planned**: 62 points (F1-F8 decomposed)

**Capacity**: 6 sprints × 16 pt/sprint = 96 points available

**Buffer**: 96 - 62 = **34 points of slack** (~2.5 sprints)

**This buffer is used for**:
1. Integration & cross-team work: ~10 points
2. Testing & QA hardening: ~10 points
3. Polish & documentation: ~8 points
4. Contingency (Plan B transitions): ~6 points

**Recommendation**:
- If using <5 points contingency by S14 → all green ✓
- If using 5-10 points → manageable, Plan B-1 light
- If using 10-15 points → activate Plan B-1 (LSTM/RL reduction)
- If using >15 points → activate Plan B-2 (F5 or F3 cut)

---

## Escalation Path

### Level 1: Dev Issue (Jules/Mikael self-resolution)

**Example**:
- Bug in scraper, fix locally
- LSTM hyperparameter, tune and rerun
- MR review comment, address and re-push

**Timeout**: 24 hours
**If unsolved**: Escalate Level 2

### Level 2: Sprint Risk (Team Retro)

**Example**:
- Story not done by Wednesday
- Velocity below target
- Test coverage dropped

**Forum**: Friday retro (45 min)
**Action**: Adjust next sprint scope or ask for support
**If unresolved**: Escalate Level 3

### Level 3: Program Risk (Project Leads)

**Example**:
- Feature slip >1 sprint
- R1 RL convergence failure
- F7 critical blocker

**Forum**: Weekly risk review (30 min, Friday 16:30)
**Action**: Activate Plan B, reallocate resources
**Owner**: Jules (sprint lead)

### Level 4: Stakeholder Escalation (If Needed)

**Example**:
- Multiple Plan B activations needed
- Soutenance date at risk
- Major scope cut required

**Forum**: Team + Professors/Sponsors
**Action**: Communicate status, reset expectations
**Owner**: Project leads

---

## Risk Response Playbook

### Playbook R1: RL Training Fails

**Checklist**:
- [ ] Verify hyperparameters (learning rate, gamma, epsilon)
- [ ] Check data quality (feature scaling, no NaNs)
- [ ] Reduce action space (BUY/HOLD only)
- [ ] Reduce training steps (50k first)
- [ ] Run DQN baseline (simpler than PPO)
- [ ] Plot loss curve (is it decreasing at all?)
- [ ] If loss flat after 50k steps → activate Plan B-1

**Estimated delay**: 1-3 days (if mitigations work)

---

### Playbook R2: Paper Trading Model Bugs

**Checklist**:
- [ ] List all test cases (long/short, SL/TP, partial fill)
- [ ] Run unit tests in isolation (no API)
- [ ] Manual testing: place 5 trades, check PnL math
- [ ] Code review: SL/TP logic line-by-line
- [ ] If >3 bugs found → pair program next day

**Estimated delay**: 2-5 days (depends on bugs)

---

### Playbook R6: Performance Issue

**Checklist**:
- [ ] Run profiler (cProfile for Python, Chrome DevTools for frontend)
- [ ] Identify bottleneck (DB query? ML prediction? Streamlit render?)
- [ ] Add index (if DB)
- [ ] Cache result (if API call repeated)
- [ ] Optimize algorithm (if ML prediction slow)
- [ ] Load test again (measure improvement)

**Estimated delay**: 1-2 days (if bottleneck clear)

---

## Success Criteria for Risk Management

✓ **Green** if:
- Risks identified and logged by S11-end
- Weekly risk reviews happen every Friday
- Mitigation actions tracked and closed
- Plan B triggers documented and ready
- No surprises in S15-S16 (RL phase)

⚠ **Orange** if:
- Risk review skipped >1 sprint
- Mitigation actions > 1 week overdue
- New risks >2/sprint identified
- Velocity trend ↓ 2 sprints

🔴 **Red** if:
- R1 (RL convergence) not addressed by S15-week2
- R2 (Model bugs) blocking F7.2 for >3 days
- Multiple high-risk items materialized without Plan B
- Soutenance date at risk without Plan B activated

---

**Document Version**: 1.0
**Last Updated**: 2026-03-14
**Review Frequency**: Weekly (Friday 16:30)
**Owner**: Jules (Sprint Lead)
