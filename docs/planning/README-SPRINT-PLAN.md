# Guide Utilisation — Plan de Sprints CryptoBot S11-S16

**Version**: 1.0
**Date**: 14 mars 2026
**Auteur**: BMAD Scrum Master (Automated)

---

## 📋 Documents du Plan

Le plan est structuré en **4 documents principaux** + 1 CSV:

### 1. **`06-sprint-plan.md`** (22 pages) — Le Plan Maître

**Contenu**:
- Résumé exécutif (métriques clés)
- Backlog priorisé (8 features, 62 story points)
- Détail des 8 user stories (F1-F8) avec acceptance criteria
- 6 sprints détaillés (S11-S16) avec goals, stories, tâches, risques
- Chemin critique et dépendances
- Stratégie QA et testing
- Métriques de succès

**À lire en priorité**: Introduction + S11 section avant de démarrer.

**Idéal pour**: Planning initial, compréhension globale, références détaillées.

---

### 2. **`06a-sprint-gantt-tracking.md`** (20 pages) — Tracking Opérationnel

**Contenu**:
- Timeline Gantt ASCII (6 sprints, 12 semaines)
- Velocity réelle vs planifiée (par sprint)
- Allocation détaillée par personne (Jules/Mikael heures)
- **⚠ ISSUE détectée**: S13 surcharge Mikael (35h > 25h max)
  - Solutions: Split LSTM ou réduire F3
- Dépendances inter-sprints (4 scénarios)
- Daily standup template (15 min)
- Sprint review checklist (Friday EOD)
- Sprint retrospective template
- Deployment checklist

**À utiliser**: Quotidiennement (standup) + hebdomadairement (review/retro).

**Idéal pour**: Tracking jour-à-jour, meetings templates, checklists.

---

### 3. **`06b-risk-mitigation.md`** (20 pages) — Gestion des Risques

**Contenu**:
- Risk registry complet (10 risques identifiés: R1-R10)
- Risk severity matrix (High/Medium/Low)
- Playbooks détaillés pour 3 risques critiques (R1 RL, R2 Model, R6 Perf)
- **Plan B options**:
  - Plan B-0: Add sprint S17 (escape hatch)
  - Plan B-1a: LSTM scope reduction (-8h)
  - Plan B-1b: RL scope reduction (-10h)
  - Plan B-1c: Combined reductions (-18h)
  - Plan B-2a: Cut F5 (on-chain)
  - Plan B-2b: Cut F3 (clustering)
  - Plan B-2c: Cut F8 (RL entirely)
- Escalation path (Level 1-4)
- Risk response playbook
- Success criteria for risk management

**À consulter**: Quand risque détecté, ou hebdomadairement (Friday risk review).

**Idéal pour**: Mitigation & contingency planning.

---

### 4. **`06c-sprint-summary.md`** (4 pages) — Résumé Exécutif

**Contenu**:
- Plan en 1 page (features, timeline, velocity, risques)
- Comment utiliser le plan (4 étapes)
- Quickstart S11 (this week)
- Key metrics to track
- ADRs (3 décisions architecturales)
- Assumptions & constraints
- Go/No-Go checklist (end S16)

**À lire**: 1ère chose, pour overview rapide.

**Idéal pour**: Stakeholders, quick reference.

---

### 5. **`06d-backlog-import.csv`** — Import Tool

**Colonnes**:
- ID, Epic, Feature, Title, Description
- Owner, Points, Sprint, Priority
- Status, Dependencies, Definition of Done, Estimated Hours

**Utilité**: Importer dans Linear/Jira/GitHub Projects directement.

**Instructions**: Copy/paste CSV dans votre outil de gestion.

---

## 🚀 Quickstart (Premier Jour)

### Étape 1: Lire le résumé (30 min)

Lisez `06c-sprint-summary.md` en entier.

**Objectif**: Comprendre le plan à haut niveau, timeline, risques clés.

### Étape 2: Explorer le plan détaillé (1h)

Lisez `06-sprint-plan.md`:
- Introduction + Executive Summary
- S11 section complète (objectif, stories, tâches, risques)

**Objectif**: Comprendre les tâches de première semaine.

### Étape 3: Setup outils (30 min)

Importer `06d-backlog-import.csv` dans votre outil (Linear, Jira, ou GitHub Projects):

```bash
# Exemple avec Linear CLI (si disponible)
linear import 06d-backlog-import.csv

# Ou manuel: Copy/paste dans Linear UI
```

### Étape 4: Kick-off meeting (30 min)

**Jules + Mikael + Scrum Master (si applicable)**:

```
Agenda:
1. Review S11 objectif (3 min)
2. Assign tâches Jules/Mikael (5 min)
3. Identify blockers/dépendances (5 min)
4. Confirm risques & mitigation (5 min)
5. Demo setup (5 min)
6. Questions (2 min)
```

---

## 📅 Utilisation par Phase

### Phase 1: Sprints 11-12 (Quick Wins)

**Documents à utiliser**:
- `06-sprint-plan.md` → S11 & S12 sections
- `06a-sprint-gantt-tracking.md` → Velocity templates, daily standup
- `06b-risk-mitigation.md` → Low-risk phase, skim only

**Fréquence**:
- Daily: 15 min standup (use template from 06a)
- Wed: Check velocity vs. track (50% burndown target)
- Friday: Sprint review + retro (use checklists from 06a)

**Outcome**: 8 points delivered (F1, F2, F3 complete)

---

### Phase 2: Sprints 13-14 (Medium + Paper Trading)

**Documents à utiliser**:
- `06-sprint-plan.md` → S13 & S14 sections
- `06a-sprint-gantt-tracking.md` → **ATTENTION: S13 overload issue** → Choose Solution
- `06b-risk-mitigation.md` → R2 (Model bugs) & R4 (Integration delays)

**Decision Required** (Sprint 12 end):

S13 has 35 hours for Mikael but capacity is 20-25h max.

**Choose one solution**:

1. **Split LSTM** (RECOMMENDED):
   - S13: LSTM features + early training (15h)
   - S14: LSTM tuning (8h)
   - Keeps RL on track ✓

2. **Reduce KMeans** (S11-12):
   - F3 core only in S11 (10h)
   - F3 viz in S12 (3h)
   - Frees ~7h in S13

3. **Delay LSTM to S14**:
   - S13: F7 focus only
   - S14: F6 + F7.3
   - Risk: LSTM less mature

**Recommendation**: Pick option 1 + 2 together = best balance.

**Fréquence**:
- Daily standup + Wed velocity check
- Friday review/retro
- **Weekly risk review** (Friday 16:30) — Consult `06b-risk-mitigation.md`

**Outcome**: 31 points delivered (F4, F5, F6, F7.1-2 complete)

---

### Phase 3: Sprints 15-16 (RL — Critical Path)

**Documents à utiliser**:
- `06-sprint-plan.md` → S15 & S16 sections
- `06a-sprint-gantt-tracking.md` → Scenario 3 (F7 slip) + Scenario 4 (Plan B)
- `06b-risk-mitigation.md` → **R1 (RL convergence) CRITICAL** → Playbook

**Critical Decision** (Sprint 14 end):

Is F7 (Paper Trading) complete?
- **YES** → Proceed S15 F8 normal ✓
- **NO** → Activate Plan B-1 (RL reduced scope) or Plan B-2c (RL cut)

**RL Training Timeline**:

S15 tasks take ~23h but RL training runs 48-72h in parallel. Start training S15-Monday, let run while doing S15 other work.

**Weekly risk review MANDATORY** (Friday 16:30):
- Is RL loss decreasing?
- Are agents converging?
- If loss flat after 50k steps → activate Plan B-1 immediately

**Fréquence**:
- Daily standup
- **Weekly risk review** + escalation path
- Friday review/retro
- S16-week1: Go/No-Go decision (F8 viable or Plan B?)

**Outcome**: 33 points delivered (F7.3, F8 partial/full, or Plan B variant)

---

## ⚠️ Warning Signs (When to Escalate)

### Red Flags — Escalate Immediately

- [ ] Story slip >1 sprint (e.g., F1 not done by end S11)
- [ ] MR open >3 days without review
- [ ] Test coverage drops <75%
- [ ] RL training loss NOT decreasing after 50k steps
- [ ] Paper trading bugs >3 in S13

**Action**: Read corresponding playbook in `06b-risk-mitigation.md`, escalate Level 2 (sprint retro) or Level 3 (Friday risk review).

### Orange Flags — Monitor Closely

- [ ] Velocity plateau <12 points for 2 consecutive sprints
- [ ] Feature at 50% done by sprint mid-week
- [ ] Pair programming needed more than 1x/week
- [ ] API integration blocking more than 2 days

**Action**: Discuss in next retro, adjust next sprint.

### Green Status

- [ ] Sprints closing on velocity target (16 ±3 points)
- [ ] MRs reviewed + merged by Friday EOD
- [ ] Coverage ≥80% maintained
- [ ] No critical blockers

---

## 🔧 How to Use in Your Tool

### Linear Setup

```bash
# 1. Create workspace (if new)
linear workspace create "CryptoBot-Sprints"

# 2. Create cycles
linear cycles create --name "S11" --start "2026-03-14" --end "2026-03-28"
linear cycles create --name "S12" --start "2026-03-29" --end "2026-04-12"
# ... etc for S13-S16

# 3. Import backlog
# Copy 06d-backlog-import.csv into Linear UI
# Or via API if available

# 4. View timeline
linear cycles view --timeline
```

### Jira Setup

```
1. Create 6 sprints (Board Settings → Sprints)
2. Import CSV (Tools → Import from CSV)
3. Map columns: ID→Epic Link, Feature→Label, Points→Story Points
4. Create board filters (By Sprint, By Owner)
5. Add dashboard: Burndown chart for each sprint
```

### GitHub Projects (Beta)

```
1. Create table view with columns: Title, Owner, Points, Sprint, Status
2. Import CSV items manually (table supports import from CSV)
3. Group by Sprint view
4. Filter by Owner for individual tracking
```

---

## 📊 Metrics Dashboard (Recommended)

Set up these **dashboards** in your tool:

### 1. Sprint Burndown (Weekly)

```
X-axis: Days (Mon-Fri)
Y-axis: Points Remaining
Line 1: Ideal trend (8→0 for S11)
Line 2: Actual trend (current)
Status: GREEN if on line, YELLOW if behind, RED if >1 day behind
```

### 2. Velocity Trend (Every Sprint)

```
Chart: Bar chart, Sprints on X, Points on Y
Bars: 1 = S11 (8), 2 = S12 (10), ... 6 = S16 (15)
Target line: 16 points (green zone ±3)
Status: RED if velocity <12 for 2+ sprints
```

### 3. Owner Utilization (Weekly)

```
Jules: Planned hours vs. actual
Mikael: Planned hours vs. actual
Target: <90% utilization (leave 10% buffer)
Alert: RED if >95% booked
```

### 4. Risk Dashboard (Weekly)

```
R1 RL: GREEN/YELLOW/RED (loss decreasing?)
R2 Model: GREEN/YELLOW/RED (bugs surfacing?)
R7 Parser: GREEN/YELLOW/RED (parse success >90%?)
Action column: If RED, activate playbook
```

---

## 📞 Escalation & Support

### Daily Issues (Use Async Communication)

**Example**: Task is blocked by missing test data.

1. Post in Slack: `#sprint-help`
2. Mention blocker with context: "F1.2 blocked: need regulatory HTML fixtures"
3. Pair if needed (30 min)
4. Document decision in PR/ticket

### Sprint Issues (Use Weekly Retro)

**Example**: Story slip detected (F1 will finish Wed instead of Tue).

1. Flag in daily standup
2. Discuss in sprint retro (Friday 16:30)
3. Decision: extend story or move to next sprint?
4. Update 06a-sprint-gantt-tracking.md with actual velocity

### Critical Issues (Use Level 3 Escalation)

**Example**: RL agents not converging (R1 triggered).

1. Detect in Friday risk review (16:30)
2. Read Playbook R1 in `06b-risk-mitigation.md`
3. Apply mitigations
4. If issue persists >24h, escalate Level 3 (Friday → Monday follow-up with leads)

---

## ✅ Go/No-Go Checklist (S16 End)

Before soutenance, verify:

- [ ] **Delivery**: All 62 story points delivered (or Plan B activated)
- [ ] **Quality**: Coverage ≥80%, CI/CD 100% success
- [ ] **Testing**: All acceptance criteria met, E2E tests pass
- [ ] **Deployment**: Staging environment working
- [ ] **Documentation**: README, docs, API schemas complete
- [ ] **Demo Ready**:
  - [ ] Signals generation working
  - [ ] Alerts sending (email + Telegram)
  - [ ] Paper trading portfolio live
  - [ ] RL agents trading (or "Phase 2 work" note)
- [ ] **Team Prepared**: Debrief on presentation, Q&A ready

**If all ✓**: READY FOR SOUTENANCE 🎉

**If any ✗**: Activate Plan B or extend timeline (if admin allows).

---

## 📚 Additional Resources

### Reading Order

1. `06c-sprint-summary.md` — Start here (5 min)
2. `06-sprint-plan.md` → Introduction + S11 (15 min)
3. `06a-sprint-gantt-tracking.md` → Use as daily reference
4. `06b-risk-mitigation.md` → Read when risk triggers

### Team Roles

| Role | Responsibility | Uses |
|------|-----------------|------|
| **Jules (Data Eng)** | F1-F5, F7.2, F4.3-4 implementation | 06, 06a, 06b |
| **Mikael (ML)** | F3, F6, F7.1, F7.3, F8 | 06, 06a, 06b |
| **Scrum Lead** (if role exists) | Velocity, risk reviews, escalations | 06a, 06b |
| **Stakeholders** | Status check, soutenance prep | 06c, 06 summary |

---

## Modifications & Updates

**This plan is living document.** Update it as you learn:

1. **After each sprint**, update actual velocity in `06a-sprint-gantt-tracking.md`
2. **When risque triggers**, log in `06b-risk-mitigation.md`
3. **If scope changes**, update `06-sprint-plan.md` and CSV
4. **Weekly**, sync updated docs to git

```bash
git add docs/06*
git commit -m "chore(sprint): update tracking after S11"
git push
```

---

## Questions?

**For questions on**:
- **Planning logic**: See `06-sprint-plan.md` section "Sprint Planning Process"
- **Tracking setup**: See `06a-sprint-gantt-tracking.md` section "Gantt Timeline Macro"
- **Risk X**: See `06b-risk-mitigation.md` → "Playbook Rx"
- **Feature Y**: See `06-sprint-plan.md` → "Detailed User Stories"

---

**Good luck! 🚀 See you at the soutenance.**

---

*Document Version 1.0*
*Generated: 2026-03-14*
*BMAD Scrum Master (Automated)*
