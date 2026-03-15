# Gantt et Tracking — CryptoBot S11-S16

---

## Gantt Timeline Macro

```
           MARS          |        AVRIL         |        MAI         |      JUIN
    14---21---28-4---11--18---25-2---9--16--23--30-7---14--21--28-4--11
    |----S11----|----S12----|----S13----|----S14----|----S15----|--S16--|

    F1  ████
    F2  ████
    F3  ████

    F4        ████████
    F5        ████████

    F6            ████████
    F7.1          ████████
    F7.2          ████████
    F7.3              ████████

    F8                            ██████████████████████
                                  (long entraînement RL)
```

---

## Velocité Réelle vs Planifiée (Tracking Template)

### Sprint 11: Quick Wins (14-28 mars)

```
Feature    | Owner  | Planned | Actual | Status     | Risk
-----------|--------|---------|--------|------------|--------
F1 Scraper | Jules  |    3    |   --   | In Progress| Low
F2 RSS     | Jules  |    2    |   --   | In Progress| Low
F3 KMeans  | Mikael |    3    |   --   | In Progress| Low
-----------|--------|---------|--------|------------|--------
TOTAL      |        |    8    |   --   | On Track   |

Burndown:
Points: 8 -> 6 (Tue) -> 4 (Wed) -> 2 (Thu) -> 0 (Fri EOD)
Status: ✓ If on line, ⚠ If behind
```

### Sprint 12: Medium (29 mars - 12 avril)

```
Feature    | Owner  | Planned | Actual | Status     | Risk
-----------|--------|---------|--------|------------|--------
F4 Alertes | Jules  |    5    |   --   | Not Started| Med
F5 OnChain | Jules  |    5    |   --   | Not Started| Med
-----------|--------|---------|--------|------------|--------
TOTAL      |        |   10    |   --   | On Track   |
```

### Sprint 13: ML + Paper Phase 1 (13-27 avril)

```
Feature    | Owner  | Planned | Actual | Status     | Risk
-----------|--------|---------|--------|------------|--------
F6 LSTM    | Mikael |    5    |   --   | Not Started| Med
F7.1 Model | Mikael |    6    |   --   | Not Started| Med
F7.2 API   | Jules  |    4    |   --   | Not Started| High*
-----------|--------|---------|--------|------------|--------
TOTAL      |        |   15    |   --   | On Track   |
* Blocked by F7.1
```

### Sprint 14: Paper Trading Frontend + Integration (28 avril - 12 mai)

```
Feature    | Owner  | Planned | Actual | Status     | Risk
-----------|--------|---------|--------|------------|--------
F7.3 UI    | Mikael |    4    |   --   | Not Started| Low
Integration| Both   |    6    |   --   | Not Started| Med
Refactor   | Both   |    6    |   --   | Not Started| Low
-----------|--------|---------|--------|------------|--------
TOTAL      |        |   16    |   --   | On Track   |
```

### Sprint 15: RL Agents (13-27 mai) — CRITICAL

```
Feature    | Owner  | Planned | Actual | Status     | Risk
-----------|--------|---------|--------|------------|--------
RL Env     | Mikael |    5    |   --   | Not Started| High
RL DQN     | Mikael |    5    |   --   | Not Started| High*
RL PPO     | Mikael |    8    |   --   | Not Started| High*
-----------|--------|---------|--------|------------|--------
TOTAL      |        |   18    |   --   | On Track   |
* Training peut être >72h, commencer tôt
```

### Sprint 16: RL Validation + Final Polish (28 mai - 11 juin)

```
Feature    | Owner  | Planned | Actual | Status     | Risk
-----------|--------|---------|--------|------------|--------
RL Valid   | Mikael |    5    |   --   | Not Started| High*
Bug Fixes  | Both   |    5    |   --   | Not Started| Med
Doc/Deploy | Both   |    5    |   --   | Not Started| Low
-----------|--------|---------|--------|------------|--------
TOTAL      |        |   15    |   --   | On Track   |
* Contingent on S15 completion
```

---

## Allocation Détaillée par Personne

### Jules (Data Engineering + Support API)

```
SPRINT 11 (8h)
├─ F1: Scraper ESMA/SEC (10h)
└─ F2: RSS ESMA/SEC (5h)
Subtotal: ~15h ✓ Within capacity (20-25h/sprint)

SPRINT 12 (17.5h)
├─ F4: Alertes SMTP/Telegram (15h)
└─ F5: Blockchain.com collector (15h)
├─ Integration + Testing (5h)
Subtotal: ~35h ⚠️ OVER — Need to split S12/S13

SPRINT 13 (7h support)
├─ F7.2: Paper trading API (7h)
└─ Support Mikael (2h)
Subtotal: ~9h ✓

SPRINT 14 (6.5h)
├─ Integration + testing (3h)
├─ Documentation (2h)
├─ Optimization (1.5h)
Subtotal: ~6.5h ✓

SPRINT 15 (0h)
└─ RL Acceleration: N/A
Subtotal: 0h ✓ (Mikael focus)

SPRINT 16 (6h)
├─ Bug fixes (3h)
├─ Documentation (2h)
├─ Deployment (1h)
Subtotal: ~6h ✓

TOTAL JULES: ~78h over 6 sprints (~13h/sprint avg)
→ Realistic, within 20-25h/sprint capacity
```

### Mikael (ML / Data Science + Frontend)

```
SPRINT 11 (20h)
├─ F3: KMeans clustering (20h)
Subtotal: 20h ✓

SPRINT 12 (0h)
└─ N/A — Focus on next
Subtotal: 0h ✓ (Buffer)

SPRINT 13 (35h) ⚠️ HEAVY
├─ F6: LSTM training (23h)
└─ F7.1: Paper trading model (12h)
Subtotal: 35h ⚠️ OVER CAPACITY
→ Solution: Move some LSTM to S14 OR cut F3 from S11

SPRINT 14 (10h)
├─ F7.3: Frontend Streamlit (7h)
├─ Testing (3h)
Subtotal: 10h ✓

SPRINT 15 (23h) CRITICAL
├─ RL Env (10h)
├─ RL DQN (5h)
├─ RL PPO (5h)
├─ Hyperparameter tuning (2h)
└─ (Entraînement 48-72h en parallèle)
Subtotal: 23h ✓ (Parallel training masks time)

SPRINT 16 (13h)
├─ RL Walk-forward validation (10h)
├─ Comparaison agents (2h)
├─ MLflow dashboard (1h)
Subtotal: 13h ✓

TOTAL MIKAEL: ~114h over 6 sprints (~19h/sprint avg)
→ AT CAPACITY — Need discipline, no scope creep
```

### ISSUE: S13 Overload

**Problema**: Mikael est surchargé S13 (35h > 25h/sprint max).

**Solutions**:

1. **Option A (Recommended)**: Split LSTM training across S13-S14
   - S13: F6 feature engineering + early epochs (15h)
   - S14: F6 final training + tuning (8h)
   - Impact: More realistic, parallel with F7.3

2. **Option B**: Reduce F3 (KMeans) scope
   - S11: KMeans core only (10h)
   - S12: KMeans visualization (3h)
   - Frees 7h in S11, space in S13

3. **Option C**: Delay F6 to S14
   - S13: F7.1 + support only (24h)
   - S14: F6 + F7.3 (18h)
   - Impact: LSTM delayed 1 sprint (maybe too late for feature maturity)

**Recommendation**: **Option A (Split LSTM)** + **Option B (KMeans S11-S12)** = Good balance.

---

## Critical Path (Pert Chart)

```
START → F1 (F7 dependency) ← F7.1 ← F7.2 ← F7.3 ← F8
         F2                  (parallel)
         F3

START (Days 0)
  ├─→ F1, F2, F3 (1 sprint = 10 days) → Day 14
  └─→ F4, F5 (1 sprint = 10 days) → Day 28
      └─→ F6 (parallel, 1.5 sprints) → Day 42
      └─→ F7.1 (1 sprint) → Day 28
          └─→ F7.2 (0.5 sprint) → Day 35
              └─→ F7.3 (0.5 sprint) → Day 42
                  └─→ F8 (2 sprints) → Day 70 (END)

CRITICAL PATH: F1/F2 → F4/F5 → F7.1 → F7.2 → F7.3 → F8 → Polish
SLACK: F3 (KMeans), F6 (LSTM) can slip 1 sprint without impact
```

---

## Dépendances Inter-Sprints

### S11 → S12 Dependencies

| Blocker | Blocked | Type | Mitigation |
|---------|---------|------|-----------|
| Signal generator running | F4 start | Logic | Already done ✓ |
| API schema frozen | F5 start | API | Already done ✓ |

→ **No blockers S11→S12** ✓

### S12 → S13 Dependencies

| Blocker | Blocked | Type | Mitigation |
|---------|---------|------|-----------|
| OHLCV + indicators in DB | F6 start | Data | Already done ✓ |
| API layer stable | F7.2 start | API | Assume S12 ok |

→ **Low risk** (F6 indépendant, F7 peut démarrer avec stub)

### S13 → S14 Dependencies

| Blocker | Blocked | Type | Mitigation |
|---------|---------|------|-----------|
| Paper trading model (F7.1) | F7.2 start | Code | Critical path, start S13 Week 1 |
| Paper trading API (F7.2) | F7.3 start | Code | Start S14 Week 1 if F7.2 done |

→ **Medium risk** (séquentialité F7.1 → F7.2 → F7.3) — **Mitigate: Parallel design**

### S14 → S15 Dependencies

| Blocker | Blocked | Type | Mitigation |
|---------|---------|------|-----------|
| Paper trading functional | F8 start | Logic | **CRITICAL** — F8 exécute trades via paper engine |

→ **HIGH risk** — F8 completely blocked by F7 completion

**Mitigation**: If F7 slips → S15 delay is 1 sprint → soutenance at risk

### S15 → S16 Dependencies

| Blocker | Blocked | Type | Mitigation |
|---------|---------|------|-----------|
| RL agents converged | F8 validation | ML | Training can overlap with S16 |

→ **Medium risk** — Use early checkpoints if not converged

---

## Scénario 1: Normal Path (No Delays)

```
Timeline (Calendar Days from 2026-03-14):

Week 1-2 (Mar 14-28):  S11 ✓ (F1, F2, F3)
Week 3-4 (Mar 29-Apr12): S12 ✓ (F4, F5)
Week 5-6 (Apr13-27):   S13 ✓ (F6, F7.1, F7.2)
Week 7-8 (Apr28-May12): S14 ✓ (F7.3, integration)
Week 9-10 (May13-27):  S15 ✓ (F8 env + agents)
Week 11-12 (May28-Jun11): S16 ✓ (F8 validation + polish)

Jun 11: Soutenance ✓✓✓
```

---

## Scénario 2: S13 Slip (LSTM delay)

```
If LSTM training misses S13:

Week 1-2 (Mar 14-28):  S11 ✓
Week 3-4 (Mar 29-Apr12): S12 ✓
Week 5-6 (Apr13-27):   S13 ~ (F7.1, F7.2, F6 partial)
Week 7-8 (Apr28-May12): S14 ~ (F7.3, F6 final, integration)
Week 9-10 (May13-27):  S15 ✓ (F8)
Week 11-12 (May28-Jun11): S16 ✓

Impact: F6 maturity reduced, RL starts as planned ✓
Acceptable: LSTM is Phase 2 optional, not MVP-blocking
```

---

## Scénario 3: F7 Slip (Paper Trading Delay) — CRITICAL

```
If F7.1 model finishes S14 instead of S13:

Week 1-2 (Mar 14-28):  S11 ✓
Week 3-4 (Mar 29-Apr12): S12 ✓
Week 5-6 (Apr13-27):   S13 ~ (F6 partial only)
Week 7-8 (Apr28-May12): S14 ~ (F7.1 final, F7.2 start)
Week 9-10 (May13-27):  S15 ~ (F7.3, F8 start late)
Week 11-12 (May28-Jun11): S16 ✓ (F8 partial)

Impact: F8 RL heavily compressed, risk incomplete
Solution: Activate Plan B (RL scope reduction)
```

---

## Scénario 4: Optimal (Plan B Activated)

```
If RL scope reduced (DQN only, 50k steps, no PPO):

S15: RL Env + DQN only (12 points instead of 18)
S16: DQN validation + polish (8 points)

Result: Faster convergence, safer delivery
Recommendation if S14 slips >2 days
```

---

## Indicateurs de Santé du Sprint

### Rouge Flags (Escalate Immediately)

- [ ] MR ouvert > 3 jours sans review
- [ ] Test coverage < 75% on new code
- [ ] Build failure > 2 heures sans fix
- [ ] Feature slip 1 sprint: activate Plan B
- [ ] Velocity trend ↓ 2 sprints consécutifs

### Orange Flags (Monitor)

- [ ] MR turnaround 24-48h
- [ ] Coverage 75-80%
- [ ] Build warning (not error)
- [ ] Feature at-risk (50% done by mid-sprint)
- [ ] Velocity plateau ±2 points

### Green Status

- [ ] All MRs merged by EOD Friday
- [ ] Coverage ≥80%
- [ ] Build 100% success
- [ ] Features on-track
- [ ] Velocity consistent ±10%

---

## Daily Standup Template (15 min, ogni giorno)

```
PARTICIPANT: Jules / Mikael
DATE: YYYY-MM-DD

1. Yesterday: What did I complete?
   - [ ] Task A (X hours)
   - [ ] Task B (Y hours)

2. Today: What will I do?
   - [ ] Task C (estimated Z hours)
   - [ ] Pair with <partner> if needed

3. Blockers: Any issues?
   - API not responding: Investigate by 2pm
   - Missing test data: Jules to provide

4. Health: Velocity on-track?
   - Velocity: X points closed / Y planned (Z%)
```

---

## Sprint Review Checklist (Friday EOD)

```
SPRINT: N (S11/S12/.../S16)
DATE: YYYY-MM-DD

1. Completed Features
   ☑ F1: Scraper → Merged, tested, staging ok
   ☑ F2: RSS → Merged, tested, staging ok
   ☐ F3: KMeans → In review (comment: silhouette low)

2. Metrics
   - Planned: 8 points
   - Completed: 5 points
   - Carryover: 3 points → S12
   - Coverage: 82% ✓
   - Build: 100% ✓

3. Velocity
   - S11 velocity: 5 → Slower than 16 pt target (reason: ...)
   - Cumulative: 5 (target 16, at-risk) ⚠

4. Risks Materialized?
   - ☑ BeautifulSoup parsing fragile (mitigated: added HTML fixtures)
   - ☐ Rate limit hit (not hit, good)

5. Demo Completed?
   - ☑ Live demo to stakeholders (video recorded)
   - Feedback: "Scraper works great, clean UI"

6. Next Sprint (S12)
   - Capacity: 25h/person
   - Committed: F4 (5pt) + F5 (5pt) = 10pt ✓
   - Risks: SMTP throttling (plan: use Mailgun)
```

---

## Sprint Retrospective Template (Friday 16:00, 45 min)

```
SPRINT: N
FACILITATOR: Jules / Mikael (rotate)

1. What went well?
   - Remote pairing worked great
   - Tests caught 3 bugs early
   - Coverage improved to 82%

2. What didn't go well?
   - Slack notifications too noisy
   - One MR blocked 2 days on review
   - LSTM hyperparameter search too slow

3. What will we do differently?
   - Set MR review SLA: <24h
   - Use Slack threads for focused chat
   - Parallelize hyperparameter search (multiprocessing)

4. Action Items
   - [ ] Jules: Set up MR review reminder (by Monday)
   - [ ] Mikael: Optimize LSTM grid search (by S13-1)

5. Velocity Analysis
   - Actual: 5 points (lower than 16 pt target)
   - Reason: Underestimation (3pt → 5h actual)
   - Adjustment: Inflate estimates by 20% going forward
```

---

## Deployment Checklist per Sprint

### After Sprint (Before Staging)

```
Sprint: S11
Date: 2026-03-28

Code Quality
- [ ] ruff check src/ passes
- [ ] mypy src/ --strict passes
- [ ] pytest tests/ --cov=src --cov-fail-under=80 passes
- [ ] No print() statements (grep -r "print(" src/)
- [ ] No secrets in code (grep -r "password\|api_key\|secret" src/)

Git/Review
- [ ] All MRs merged to main
- [ ] Commit messages follow conventional format
- [ ] Code review comments resolved

Deployment
- [ ] docker-compose build (all images OK)
- [ ] docker-compose up (healthcheck passes)
- [ ] smoke test (GET /api/health returns 200)
- [ ] Database migrations applied
- [ ] MinIO buckets accessible

Before Production (S16 only)
- [ ] Load test: 100 req/s x 60s
- [ ] Data backup tested (restore works)
- [ ] Monitoring dashboards active
- [ ] Alerting rules configured
```

---

**Document Version**: 1.0
**Date**: 2026-03-14
**Keep Updated**: Weekly during each sprint
