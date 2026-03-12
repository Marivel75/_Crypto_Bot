# ML/Data Science Specification (CDC) — Crypto Bot

**Document:** `01-requirements.md` (1,246 lines)  
**Version:** 2.0  
**Date:** 2026-03-12  
**Language:** French  
**Audience:** ML team, PM, QA, Orchestrator, Auditors

---

## Quick Start

This folder contains the **Cahier des Charges (CDC)** — comprehensive specification for the ML/Data Science module (`src/ml/`).

### Document Overview

| Section | Purpose | Key Points |
|---------|---------|-----------|
| Executive Summary | Architecture & principles | 2-phase (Rule Engine v1 + Supervised ML v2) |
| RF-ML-001 to RF-ML-030 | Functional requirements | Rule engine, feature engineering, training, backtesting, signalling, MLOps, NLP, monitoring |
| RNF-ML-001 to RNF-ML-006 | Non-functional requirements | Performance, accuracy, reproducibility, logging, type hints, test coverage |
| Traceability Matrix (§10) | Maps requirements to code | RF-ML-001 → `src/ml/rules/engine.py:43-59` |
| Audit Remediation (§11) | Addresses audit.md findings | T1-T7 with effort estimates & implementation plan |
| Deployment Plan (§12) | 3-phase rollout | Week 1-2: remediation, Week 3-4: MVP, Week 5+: production-ready |
| Acceptance Criteria (§13) | Definition of done | Code quality, testing, documentation, performance, MLOps |

---

## How to Use This Specification

### For ML Engineers

1. **Read the full document:**
   ```bash
   cat 01-requirements.md | less
   ```

2. **Understand your requirements:**
   - Search for `RF-ML-XXX` matching your task
   - Each requirement has: MoSCoW priority, description, acceptance criteria (checkboxes), dependencies

3. **Implement with TDD:**
   - Create tests first (see "Test Locations" in §10)
   - Implement to pass tests
   - Reference `Fichiers associés` for file paths

4. **Quality gates before committing:**
   ```bash
   ruff check src/ml/ --fix && ruff format src/ml/
   mypy src/ml/ --strict
   pytest tests/ --cov=src/ml --cov-fail-under=80
   ```

### For Code Reviewers

1. **Verify against CDC:**
   - Does the PR implement a specific RF-ML-XXX or RNF-ML-XXX?
   - Are all acceptance criteria checkboxes addressed?
   - Do tests cover all scenarios listed in the requirement?

2. **Check traceability:**
   - Section 10 matrix: is the changed file mentioned as `Fichiers associés`?
   - Is the test file corresponding to the requirement present?

3. **Validate test coverage:**
   - All RF-ML-001 to RF-ML-030 tested individually?
   - E2E test included (RF-ML-021: signal pipeline)?
   - `pytest --cov=src/ml` shows ≥80%?

### For QA / Testers

1. **Extract test scenarios** from each RF-ML-XXX:
   - Look for `Acceptation :` section (checkboxes)
   - Each checkbox = one test case

2. **Example (RF-ML-002 — RSI Multi-TF):**
   ```
   Test 1: evaluate_rsi detects overbought convergence → emits RuleResult
   Test 2: evaluate_rsi detects oversold convergence → emits RuleResult
   Test 3: evaluate_rsi finds no convergence → returns None
   Test 4: evaluate_rsi handles missing timeframe → handles gracefully
   ```

3. **Reference test files:** See "Fichiers associés" in each requirement

### For Auditors / Compliance

1. **Audit findings addressed:**
   - §11 maps each audit issue (T1-T7, A1-A5) to remediation
   - Effort estimates provided

2. **Example (T1 — Code ML excluded):**
   - Issue: ML code has 0 test coverage
   - Resolution: RNF-ML-006 requires ≥80% coverage, enforce in CI
   - Effort: 1 hour to fix pyproject.toml + CI gate

3. **Sign-off:** Document completion validates audit remediation

---

## Requirement ID Naming Convention

```
RF-ML-001 = Functional Requirement, ML module, 001st requirement
   │   │     │
   │   │     └─ Sequential number (001-030)
   │   └─────── Module (ML)
   └──────────── Type (RF=Functional, RNF=Non-Functional)

RNF-ML-001 = Non-Functional Requirement, ML module, 001st
```

---

## MoSCoW Priority Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **MUST** | Mandatory for MVP | Implement in phase 1-2 |
| **SHOULD** | Important but can defer | Implement in phase 2-3 if time |
| **COULD** | Nice-to-have | Implement in phase 3+ |

Example breakdown:
- **MUST (15):** RF-ML-001-007, 009-010, 013-022
- **SHOULD (12):** RF-ML-004, 011-012, 024-025, 029-030
- **COULD (3):** RF-ML-012 (LSTM), 026 (sentiment), 029 (drift — optional Phase 2+)

---

## Quick Reference: Key File Locations

### Rule Engine (Phase 1)
```
src/ml/rules/
├── engine.py           # RuleEngine class, aggregation logic (RF-ML-001, 007)
├── rsi_rules.py        # RSI convergence (RF-ML-002)
├── bollinger_rules.py  # Bollinger Bands (RF-ML-003)
├── harmonic_rules.py   # Harmonic patterns (RF-ML-004)
├── trend_rules.py      # Trend lines (RF-ML-005)
├── multi_tf_rules.py   # Multi-TF alignment (RF-ML-006)
└── models.py           # RuleResult dataclass
```

### Model Training (Phase 2)
```
src/ml/models/
├── feature_engineering.py  # build_feature_matrix (RF-ML-008)
├── trainer.py              # ModelTrainer class (RF-ML-009, 010)
├── predictor.py            # Model inference
└── backtester.py           # Legacy backtester
```

### Backtesting
```
src/ml/backtesting/
├── backtest_engine.py      # WalkForwardBacktester (RF-ML-013-015)
└── metrics.py              # Sharpe, win_rate, profit_factor
```

### Signal Generation
```
src/ml/
├── signal_generator.py     # SignalGenerator orchestration (RF-ML-016-020)
└── repositories/
    └── timescale.py        # Data fetch (RF-ML-021)
```

### MLOps & NLP
```
src/ml/
├── mlflow_utils.py         # MLflow helpers (RF-ML-023-024)
├── config/
│   └── indicators.yaml     # Indicator thresholds (RF-ML-001)
└── nlp/
    ├── sentiment.py        # SentimentAnalyzer (RF-ML-026)
    └── text_mining.py      # Text preprocessing
```

---

## Implementation Roadmap

### Phase 1: Audit Remediation (Week 1-2) — 30 hours
Priority: **CRITICAL** (blocks production deployment)

| Task | Issue | Effort | Status |
|------|-------|--------|--------|
| Include ML in coverage | T1 | 1h | — |
| Test WalkForwardBacktester | T2 | 8h | — |
| E2E signal pipeline test | T3 | 6h | — |
| Fix RuleEngine API | T4 | 2h | — |
| Verify feature engineering | T5 | 3h | — |
| Add freeze_time to tests | T6 | 2h | — |
| Test signal thresholds | T7 | 3h | — |
| Type hints compliance | A1 | 2h | — |
| Coverage gate CI | RNF-ML-006 | 2h | — |

### Phase 2: MVP (Week 3-4) — 48 hours
Priority: **HIGH** (Phase 1 complete)

Implement RF-ML-001 through RF-ML-020:
- Rule engine (RF-ML-001-007)
- Feature engineering (RF-ML-008-009)
- XGBoost training (RF-ML-010)
- Walk-forward backtesting (RF-ML-013-015)
- Signal generation (RF-ML-016-020)

### Phase 3: Production Ready (Week 5+) — 28 hours
Priority: **MEDIUM** (post-MVP)

Add RF-ML-021 through RF-ML-030:
- Async pipeline (RF-ML-021-022)
- MLflow + DVC (RF-ML-023-025)
- Sentiment analysis (RF-ML-026-028)
- Concept drift (RF-ML-029-030)

---

## Testing Checklist (per Requirement)

For each RF-ML-XXX, ensure:

1. **Unit Test** (`tests/unit/test_*.py`)
   - Mocks external dependencies
   - Tests happy path + edge cases
   - No I/O (fast, < 1s per test)

2. **Integration Test** (`tests/integration/test_*.py`)
   - Real TimescaleDB (or docker-compose service)
   - Data fixtures from repo
   - Tests cross-component interactions

3. **E2E Test** (`tests/e2e/test_signal_e2e.py`)
   - Full pipeline: ETL → ML → API → Frontend
   - Run once per phase (comprehensive)

---

## Audit Remediation Status

### T1: ML code excluded from coverage
- **CDC Requirement:** RNF-ML-006 (test coverage ≥80%)
- **Fix:** Remove `omit = ["src/ml/*"]` from `pyproject.toml`
- **Verify:** `pytest --cov=src/ml --cov-fail-under=80` passes
- **Effort:** 1 hour

### T2: WalkForwardBacktester untested
- **CDC Requirements:** RF-ML-013, RF-ML-014, RF-ML-015
- **Fix:** Implement `tests/unit/test_backtest_engine.py` with full coverage
- **Effort:** 8 hours

### T3: No E2E signal pipeline test
- **CDC Requirements:** RF-ML-021, RF-ML-022
- **Fix:** Implement `tests/integration/test_signal_e2e.py`
- **Effort:** 6 hours

### T4: Double RuleEngine API
- **CDC Requirement:** RF-ML-016
- **Fix:** Standardize to single public method
- **Effort:** 2 hours

### T5: Feature engineering data leakage
- **CDC Requirements:** RF-ML-008, RF-ML-009
- **Fix:** Verify temporal split before feature calculation
- **Effort:** 3 hours

### T6: No @freeze_time in tests
- **CDC Requirement:** RNF-ML-003 (reproducibility)
- **Fix:** Add `@freeze_time()` to all temporal tests
- **Effort:** 2 hours

### T7: No signal threshold regression tests
- **CDC Requirements:** RF-ML-017, RF-ML-018, RF-ML-019
- **Fix:** Implement `tests/unit/test_signal_thresholds.py`
- **Effort:** 3 hours

---

## Quality Gates (Pre-Merge)

All of the following must pass:

```bash
# 1. Lint & format
ruff check src/ml/ --fix
ruff format src/ml/

# 2. Type checking
mypy src/ml/ --strict

# 3. Unit & integration tests
pytest tests/unit/ tests/integration/ -v

# 4. Coverage gate
pytest tests/ --cov=src/ml --cov-fail-under=80 --cov-report=html

# 5. E2E test (optional, resource-intensive)
docker-compose up -d && pytest tests/e2e/ -v && docker-compose down
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-01 | ML team | Initial draft (incomplete) |
| 2.0 | 2026-03-12 | PM ML + Analyst ML | Complete specification with 30 RF, audit remediation, traceability |

---

## Approval & Sign-Off

- [ ] **ML Team Lead** — reviewed requirements, feasible?
- [ ] **Orchestrator** — aligned with cross-team dependencies?
- [ ] **QA Lead** — test plan comprehensive?
- [ ] **Audit** — all findings addressed?

---

## Questions?

Refer to:
- **Architecture:** §1 Executive Summary + Section §4-9 specific modules
- **Audit issues:** §11 Remédiation Audit (T1-T7 with effort estimates)
- **Implementation:** §12 Plan de Déploiement (phased roadmap)
- **Code locations:** §10 Matrice de Traçabilité (RF-ML-XXX → source files)
- **Definitions:** Each RF-ML-XXX has acceptance criteria (checkboxes) and test locations

Document is **machine-readable** — grep for RFC IDs:
```bash
grep -n "RF-ML-016" 01-requirements.md  # Find requirement #16
grep -n "src/ml/signal_generator.py" 01-requirements.md  # Find all refs to a file
```

---

**Final Note:** This CDC is the **single source of truth** for ML module specification. All implementation, testing, and review must reference this document. Changes to requirements require RFC amendment + team approval.

