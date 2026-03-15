# Résumé Plan de Sprints — CryptoBot S11-S16

**Date**: 14 mars 2026
**Équipe**: Jules (Data Engineering) + Mikael (ML/Data Science)
**Soutenance**: juin 2026 (~12 semaines)

---

## En Une Page

### Portée

| Feature | Owner | Points | Sprint | État |
|---------|-------|--------|--------|------|
| **F1** Scraping réglementaire | Jules | 3 | S11 | Ready |
| **F2** RSS ESMA/SEC | Jules | 2 | S11 | Ready |
| **F3** K-Means clustering | Mikael | 3 | S11 | Ready |
| **F4** Alertes (SMTP+Telegram) | Jules | 5 | S12 | Ready |
| **F5** Données on-chain | Jules | 5 | S12 | Ready |
| **F6** LSTM deep learning | Mikael | 5 | S13 | Ready |
| **F7** Paper trading (full stack) | Mikael+Jules | 13 | S13-S14 | **CRITICAL** |
| **F8** RL agents (DQN+PPO) | Mikael | 21 | S15-S16 | **CRITICAL PATH** |
| | | **62 pt total** | | |

### Timeline

```
S11: Quick wins (8 pts)    ▓▓▓▓▓▓░░░░░░░░░░░░░░  ✓ Low risk
S12: Medium (10 pts)       ░░░░▓▓▓▓▓▓░░░░░░░░░░  ✓ Low risk
S13: ML + Paper P1 (15 pts) ░░░░░░░░▓▓▓▓▓▓▓░░░░░░  ⚠ Medium risk
S14: Paper P2+Integration (16 pts) ░░░░░░░░░░░░░░░▓▓▓▓▓▓  ⚠ Medium risk
S15: RL P1-2 (18 pts)      ░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓  🔴 HIGH risk
S16: RL P3-4 + Polish (15 pts) ░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓ 🔴 HIGH risk
```

### Velocity

- **Planned**: 16 points/sprint (average)
- **Capacity**: 20-25 hours/person/sprint
- **Buffer**: 34 points (2.5 sprints) for contingency
- **Status**: Realistic, with Plan B options

### Risques Critiques

| Risk | Probabilité | Trigger | Mitigation |
|------|----------|---------|-----------|
| **R1: RL convergence fail** | MEDIUM (50%) | Loss flat S15-week2 | Plan B-1 (DQN only) |
| **R2: Paper trading bugs** | MEDIUM (40%) | >3 bugs in S13 | Pair program, unit tests |
| **R7: Scraper fragility** | MEDIUM (35%) | Parse success <90% | Fallback selectors, fixtures |

### Plan B (If needed)

- **Plan B-1**: Reduce LSTM + RL scope → saves 18h, delivers MVP
- **Plan B-2**: Cut F5 (on-chain) or F3 (clustering) → saves 5-3h each
- **Plan B-3**: Cut F8 (RL entirely) → MVP still complete

---

## Documents de Référence

### 1. **`06-sprint-plan.md`** — Plan détaillé (22 pages)
   - Backlog priorisé avec story points
   - 6 sprints détaillés (objectifs, stories, tâches, risks)
   - Dépendances et chemin critique
   - Definition of Done pour chaque feature
   - Stratégie QA et testing

### 2. **`06a-sprint-gantt-tracking.md`** — Gantt + Métriques (20 pages)
   - Timeline Gantt ASCII
   - Allocation par personne (Jules/Mikael)
   - Velocity tracking templates
   - Dépendances inter-sprints (scenarios 1-4)
   - Daily standup + sprint review checklists
   - Deployment checklist

### 3. **`06b-risk-mitigation.md`** — Gestion des risques (20 pages)
   - Risk registry complète (10 risques identifiés)
   - Risk severity matrix
   - Playbooks pour R1, R2, R6
   - Plan B options (B-0 à B-2c)
   - Escalation path
   - Success criteria

### 4. **`06c-sprint-summary.md`** — **Ce document** (résumé 1 page)

---

## Comment Utiliser le Plan

### Pour Démarrer

1. **Lisez** `06-sprint-plan.md` Introduction + S11 section
2. **Préparez** les tâches S11 (T1.1-T3.6)
3. **Setup** sprints dans Jira/Linear/GitHub Projects
4. **Lancez** Friday S11-end: sprint review + retro

### Pendant Chaque Sprint

**Lundi matin**:
- [ ] Vérifiez `06a-sprint-gantt-tracking.md` — Allocation cette semaine
- [ ] Sync avec partenaire (pair setup si bloqué)

**Quotidien (15 min)** — Daily standup template `06a-sprint-gantt-tracking.md`

**Mercredi EOD** — Vérifiez velocity vs. track (half-sprint burn)

**Vendredi** — Sprint review + retro (templates in `06a`)

**Riskwise** — Weekly risk review vendredi 16:30 (template `06b-risk-mitigation.md`)

### Si Blocker / Risque

1. **Consultez** `06b-risk-mitigation.md` → Risk Registry → trouvez R#
2. **Lisez** Playbook correspondant
3. **Appliquez** Mitigation
4. **Escaladez** si non résolu en 24h (Level 2 → Sprint retro)

### Si Slip >1 Sprint

1. **Activez** Plan B correspondant (voir `06b Risk B-1/B-2/B-3`)
2. **Communiquez** changement de scope
3. **Réallocuez** temps aux features prioritaires (Paper Trading > RL)

---

## Quickstart: S11 (14-28 mars)

### Goals
- Complete F1 (Scraper) et F2 (RSS) → Jules
- Complete F3 (KMeans) → Mikael
- Velocity: 8 points → establish baseline

### Tâches à Faire (This Week)

**Jules** (16h planned):
```
Day 1-2: F1 Scraper (T1.1-T1.5) — 12h
Day 2-3: F2 RSS (T2.1-T2.4) — 5h
Day 3: Code review + merge — 1h
```

**Mikael** (20h planned):
```
Day 1-3: F3 KMeans pipeline (T3.1-T3.6) — 20h
Day 3: Testing + MLflow — 3h
```

### Success Criteria S11-end

- [ ] All MRs merged to main (`data-eng/regulatory-scraper`, `data-eng/rss-collector`, `ml/clustering`)
- [ ] Coverage ≥80%
- [ ] Logs show: ≥1 regulatory doc scraped, ≥2 RSS feeds parsed, clusters stable
- [ ] Velocity achieved: 8 points
- [ ] Demo Friday: Show documents + RSS + clusters in Streamlit

---

## Key Metrics to Track

### Per Sprint

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Velocity (points) | 16 | -- | -- |
| Coverage (%) | ≥80% | -- | -- |
| MR review turnaround (hours) | <24h | -- | -- |
| Build success (%) | 100% | -- | -- |
| Sprint goal completion (%) | ≥90% | -- | -- |

### Cumulative (Through S16)

| Metric | Target |
|--------|--------|
| Total points delivered | 62 |
| Defects escaped to prod | <3 |
| Rework % of velocity | <10% |
| Unplanned work % | <5% |

---

## Key Decisions (ADRs)

### ADR-SPR-001: Split F7 into 3 stories (P1, P2, P3)

**Why**: Paper trading complex, better to track modèle + API + frontend separately.

**Impact**: Clearer dependencies, easier handoff between Mikael → Jules → Mikael.

---

### ADR-SPR-002: Reduce RL agents to DQN primary, PPO secondary

**Why**: DQN simpler to train, converges faster, PPO can be Phase 2 work.

**Impact**: F8 scope more achievable, Plan B-1 viable.

---

### ADR-SPR-003: Use Plan B-1 as primary contingency

**Why**: LSTM reduction + RL scope reduction = 18h saved, doesn't break MVP.

**Impact**: If S13 slip, can recover in S15 without full scope cut.

---

## Assumptions

- ✓ Infrastructure (Docker, TimescaleDB, MinIO) already working
- ✓ Signal generator + rule engine implemented
- ✓ API + Frontend scaffolds in place
- ✓ 2 developers, part-time (~25h/person/week)
- ✓ Soutenance date: June 2026 (immovable)
- ✓ No major architecture changes needed

---

## Go/No-Go Checklist (End S16)

**READY FOR SOUTENANCE if**:

- [ ] All 62 story points delivered (or Plan B activated)
- [ ] Coverage ≥80%
- [ ] CI/CD pipeline 100% success
- [ ] Staging deployment working
- [ ] Démo live ready:
  - [ ] Signals generated + displayed
  - [ ] Alerts sent (email + Telegram)
  - [ ] Paper trading portfolio live
  - [ ] RL agents trading (or marked future work)
- [ ] Documentation complete
- [ ] Team debriefed on soutenance flow

---

## Contact & Escalation

**Sprint Lead (Risk Escalation)**: Jules

**Daily Sync**: Async (Slack) + Friday sync call

**Weekly Risk Review**: Friday 16:30

**If blocked**: Tag with risk ID (R1, R2, etc.) + playbook

---

## Next Steps

1. **Copy sprint plan to project management tool** (Linear, Jira, GitHub Projects)
2. **Schedule S11 kickoff** — Monday 2026-03-14 morning
3. **Prepare dev environment** — Confirm Docker/DB/MinIO running
4. **Review risk playbooks** — Both team members familiar with `06b-risk-mitigation.md`
5. **Setup CI/CD monitoring** — Slack alerts on build failures
6. **Book Friday demo slots** — Soutenance professors availability

---

**Pour toutes questions**: Consultez les documents complémentaires (06, 06a, 06b).

**Bonne chance! 🚀**

---

*Document Version 1.0*
*Generated: 2026-03-14*
*BMAD Scrum Master (Automated)*
