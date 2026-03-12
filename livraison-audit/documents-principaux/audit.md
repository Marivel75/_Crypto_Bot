# Audit Complet — Crypto Bot

**Date :** 2026-03-12
**Auditeurs :** 5 agents spécialisés (Architecture, Sécurité, DevOps, Testing/ML, Documentation)
**Périmètre :** Codebase entier, configuration, infrastructure, documentation

---

## Note Globale : B+

| Domaine | Note | Critique | Haut | Moyen | Bas |
|---------|------|----------|------|-------|-----|
| Architecture & Qualité | A- | 0 | 0 | 5 | 0 |
| Sécurité | C | 3 | 5 | 3 | 1 |
| DevOps & Infrastructure | C+ | 2 | 5 | 3 | 0 |
| Testing & ML Pipeline | C | 3 | 0 | 4 | 0 |
| Documentation & Complétude | B | 0 | 2 | 3 | 0 |
| **Total** | | **8** | **12** | **18** | **1** |

**Verdict :** Le projet est bien structuré et architecturalement solide, mais **ne doit PAS être déployé en production** tant que les 8 issues critiques ne sont pas résolues.

---

## 1. Architecture & Qualité du Code (A-)

### Points forts

- **Séparation en 5 équipes** (ETL, ML, API, Frontend, DevOps) avec des frontières claires
- **Modèles Pydantic v2** utilisés de manière cohérente pour la validation des données
- **Pattern Repository** correctement implémenté dans les services API
- **Async/await** pour toutes les opérations I/O (SQLAlchemy async, httpx)
- **Configuration centralisée** via `pydantic-settings` dans `src/shared/config.py`
- **Gestion d'erreurs structurée** avec hiérarchie d'exceptions dans `src/shared/exceptions.py`

### Issues (5 MEDIUM)

| # | Issue | Fichier(s) | Impact |
|---|-------|-----------|--------|
| A1 | 23 `# type: ignore` dans `api_client.py` | `src/frontend/api_client.py` | Masque des erreurs de type potentielles |
| A2 | Confusion ORM aliasing : `orm.py` vs `db_models.py` | `src/shared/`, `src/api/` | Ambiguïté pour les développeurs |
| A3 | Réponses API non typées dans certains endpoints | `src/api/routers/` | Perte de la garantie de type |
| A4 | Services ML importent directement les constantes au lieu de passer par config | `src/ml/` | Couplage fort |
| A5 | `etl/main.py` mélange scheduling et logique métier | `src/etl/main.py` | Violation SRP, testabilité réduite |

### Recommandations

1. **A1** — Résoudre les `type: ignore` un par un en ajoutant les types corrects aux réponses API
2. **A2** — Standardiser sur un seul nom (`db_models.py`) et supprimer les alias
3. **A3** — Ajouter `response_model` explicite sur chaque endpoint
4. **A4** — Passer les seuils d'indicateurs via `Settings` ou un fichier `config/indicators.yaml`
5. **A5** — Extraire les jobs du scheduler dans des modules séparés

---

## 2. Sécurité (C)

> Rapport détaillé : [`SECURITY_AUDIT.md`](./SECURITY_AUDIT.md)

### CRITICAL (3)

| # | Issue | Risque |
|---|-------|--------|
| S1 | Secrets hardcodés dans `src/shared/config.py` (defaults Pydantic) | Secrets dans bytecode, images Docker, git history |
| S2 | Mot de passe DB visible dans commande MLflow (`docker ps`) | Credentials lisibles dans `/proc/[pid]/cmdline` |
| S3 | Credentials par défaut (`admin:admin`, `minioadmin`) dans compose | Exploitation via Shodan/scans automatisés |

### HIGH (5)

| # | Issue | Risque |
|---|-------|--------|
| S4 | Validation manquante sur endpoints signals/watchlist | Injection de caractères spéciaux |
| S5 | CORS trop permissif (`allow_methods=["*"]`) | Requêtes cross-origin non autorisées |
| S6 | HTTPS redirect commenté dans Nginx | Credentials en clair sur le réseau |
| S7 | Headers de sécurité manquants sur le frontend | Clickjacking, MIME-sniffing |
| S8 | Images Docker base non pinnées (`:slim` sans version patch) | Attaque supply chain |

### MEDIUM (3)

| # | Issue |
|---|-------|
| S9 | Logique d'échappement LIKE fragile dans `news_service.py` |
| S10 | Champ `username` optionnel dans JWT (fuite d'info) |
| S11 | Healthcheck ETL pointe sur un endpoint HTTP inexistant |

### LOW (1)

| # | Issue |
|---|-------|
| S12 | URL API frontend non validée (risque de token leak) |

### Points positifs sécurité

- bcrypt pour les mots de passe (12 rounds)
- JWT HS256 avec expiration + validation correcte
- Requêtes SQL 100% paramétrées (SQLAlchemy ORM)
- Multi-stage Docker builds, user non-root (UID 1001)
- Rate limiting Nginx sur les endpoints d'auth
- `.env` correctement gitignored, `.env.example` avec placeholders

---

## 3. DevOps & Infrastructure (C+)

### CRITICAL (2)

| # | Issue | Fichier | Impact |
|---|-------|---------|--------|
| D1 | Images Docker unpinnées (`:latest` implicite sur `timescaledb`, `minio`, `grafana`) | `docker-compose.yml` | Builds non-reproductibles, risque supply chain |
| D2 | Ansible `synchronize` avec `delete: true` peut effacer `.env` en prod | `infra/ansible/` | Perte de configuration, downtime |

### HIGH (5)

| # | Issue | Impact |
|---|-------|--------|
| D3 | Pas de mécanisme de rollback dans le déploiement | Impossible de revenir en arrière si deploy cassé |
| D4 | CI utilise `--no-cache` systématiquement | Builds lents (5-10 min au lieu de 1-2 min) |
| D5 | Données MinIO non sauvegardées (seul TimescaleDB a un backup) | Perte de modèles ML, datasets, artifacts MLflow |
| D6 | Pas de monitoring d'alertes (Grafana configuré mais pas d'alertes) | Pannes silencieuses |
| D7 | GitHub Actions secrets non configurés (référencés mais pas créés) | CI échoue en production |

### MEDIUM (3)

| # | Issue |
|---|-------|
| D8 | Docker Compose `version: "3.8"` obsolète (ignoré depuis Compose V2) |
| D9 | Nginx logs en volume anonyme (perte au restart) |
| D10 | Pas de `docker-compose.override.yml` pour dev vs prod |

### Recommandations prioritaires

1. **Pinner toutes les images** : `timescaledb/timescaledb:2.14.2-pg16`, `minio/minio:RELEASE.2024-01-01`, etc.
2. **Ajouter un script de rollback** : garder les 3 dernières versions d'images, script `rollback.sh`
3. **Backup MinIO** : `mc mirror` quotidien vers un bucket de backup ou un volume externe
4. **Configurer les alertes Grafana** : CPU > 80%, mémoire > 80%, healthcheck failed, API latence > 2s
5. **Corriger Ansible** : remplacer `delete: true` par `delete: false`, utiliser `exclude` pour `.env`

---

## 4. Testing & ML Pipeline (C)

### CRITICAL (3)

| # | Issue | Impact |
|---|-------|--------|
| T1 | Code ML exclu de la couverture de tests (trainer, predictor, backtesting) | Couverture réelle ~50-60%, pas 80% |
| T2 | `WalkForwardBacktester` non testé — les tests importent la mauvaise classe (`Backtester`) | Composant critique non validé |
| T3 | Pas de test E2E du pipeline de signaux async (ETL → ML → API → Frontend) | Flux principal non couvert |

### MEDIUM (4)

| # | Issue |
|---|-------|
| T4 | Rule engine a une double API (méthodes `evaluate` et `generate_signals`) — fragile et confusant |
| T5 | Feature engineering potentiellement affecté par data leakage (indicators calculés avant split temporel) |
| T6 | Tests ML utilisent des seeds aléatoires mais pas `@freeze_time` pour les timestamps |
| T7 | Pas de test de régression pour les seuils de signaux (confidence >= 0.6) |

### Couverture réelle estimée

```
Module              Déclarée    Réelle (estimée)
─────────────────────────────────────────────────
src/api/            85%         85%         ✅
src/etl/            75%         70%         ⚠️
src/ml/             80%         50-60%      ❌
src/shared/         90%         90%         ✅
src/frontend/       60%         55%         ⚠️
─────────────────────────────────────────────────
Global              80%         65-70%      ❌
```

### Recommandations

1. **Inclure le code ML dans la couverture** : retirer les exclusions de `pyproject.toml` / `.coveragerc`
2. **Corriger l'import** dans les tests de backtesting : `from src.ml.backtesting import WalkForwardBacktester`
3. **Ajouter un test E2E** : collecte OHLCV → rule engine → signal generation → API retrieval
4. **Unifier l'API du rule engine** : garder uniquement `generate_signals()`, déprécier `evaluate()`
5. **Ajouter des tests de régression** pour les seuils critiques (confidence, leverage, margin)

---

## 5. Documentation & Complétude (~75%)

### Maturité par domaine

| Domaine | Complétude | Notes |
|---------|-----------|-------|
| `docs/00-overview.md` | 95% | Excellent, vision claire |
| `docs/01-data-engineering.md` | 80% | Manque les schémas TimescaleDB détaillés |
| `docs/02-ml-data-science.md` | 85% | Bon, mais backtesting walk-forward peu documenté |
| `docs/03-backend-api.md` | 90% | Bien structuré, endpoints documentés |
| `docs/04-frontend-ui.md` | 70% | Manque les wireframes et user flows |
| `docs/05-devops-infra.md` | 75% | Manque le runbook de production |
| `docs/06-roadmap.md` | 60% | KPIs définis mais pas de timeline précise |
| `CLAUDE.md` | 95% | Complet, conventions claires |
| `.env.example` | 80% | Manque les commentaires de sécurité |

### HIGH (2)

| # | Issue | Impact |
|---|-------|--------|
| C1 | Pas de runbook de production (procédures d'incidents, contacts, rollback) | Équipe perdue en cas de panne |
| C2 | Incohérence version PostgreSQL : `pg12` dans certains fichiers, `pg16` dans d'autres | Confusion, bugs potentiels |

### MEDIUM (3)

| # | Issue |
|---|-------|
| C3 | Migrations Alembic stagnantes — une seule migration de nov 2024 |
| C4 | GitHub Actions secrets documentés mais non créés |
| C5 | Rate limiting documenté mais implémentation non vérifiable (Nginx seulement) |

---

## Plan de Remédiation

### Phase 1 — Bloquants (Semaine 1)

| Priorité | Issue | Effort | Responsable |
|----------|-------|--------|-------------|
| P0 | S1 — Supprimer secrets hardcodés de `config.py` | 30 min | Backend |
| P0 | S2 — MLflow : passer DB creds en env vars | 20 min | DevOps |
| P0 | S3 — Forcer des mots de passe forts (pas de defaults) | 45 min | DevOps |
| P0 | D1 — Pinner toutes les images Docker | 30 min | DevOps |
| P0 | D2 — Corriger Ansible `delete: true` | 15 min | DevOps |
| P0 | T1 — Inclure code ML dans la couverture | 1h | ML |
| P0 | T2 — Corriger import `WalkForwardBacktester` dans les tests | 15 min | ML |
| P0 | T3 — Écrire test E2E pipeline de signaux | 2h | Transversal |

### Phase 2 — Avant Production (Semaine 2-3)

| Priorité | Issue | Effort |
|----------|-------|--------|
| P1 | S4 — Validation input signals/watchlist | 15 min |
| P1 | S5 — Restreindre CORS | 10 min |
| P1 | S6 — Activer HTTPS + Let's Encrypt | 1h |
| P1 | S7 — Headers sécurité Nginx (frontend) | 10 min |
| P1 | S8 — Pinner images Docker Python | 10 min |
| P1 | D3 — Script de rollback | 2h |
| P1 | D5 — Backup MinIO | 1h |
| P1 | C1 — Écrire runbook de production | 2h |
| P1 | C2 — Harmoniser version PostgreSQL (pg16) | 30 min |

### Phase 3 — Améliorations (Semaine 4+)

| Priorité | Issue | Effort |
|----------|-------|--------|
| P2 | A1-A5 — Issues architecture | 4h total |
| P2 | T4-T7 — Issues testing/ML | 3h total |
| P2 | S9-S12 — Issues sécurité medium/low | 1h total |
| P2 | D6-D10 — Issues DevOps medium | 3h total |
| P2 | C3-C5 — Issues documentation | 2h total |

---

## Métriques Clés

| Métrique | Actuel | Cible |
|----------|--------|-------|
| Couverture de tests réelle | ~65-70% | ≥80% |
| Vulnérabilités CRITICAL | 8 | 0 |
| Vulnérabilités HIGH | 12 | 0 |
| Images Docker pinnées | 3/8 | 8/8 |
| Migrations Alembic à jour | Non | Oui |
| Runbook de production | Absent | Complet |
| Backup MinIO | Absent | Quotidien |
| Alertes Grafana | 0 | ≥5 règles |
| HTTPS activé | Non | Oui |

---

## Conclusion

Le projet Crypto Bot présente une **architecture solide** (note A-) avec une bonne séparation des responsabilités, des patterns modernes (async, Pydantic v2, Repository), et une documentation de qualité. Les conventions de code et la configuration Claude Code sont exemplaires.

Cependant, **la sécurité et l'infrastructure ne sont pas prêtes pour la production**. Les 3 vulnérabilités critiques de sécurité (secrets hardcodés, credentials exposées) et les 2 problèmes critiques DevOps (images non pinnées, Ansible destructif) doivent être résolus en priorité absolue.

Le pipeline ML souffre d'un **manque de couverture réelle** — la couverture déclarée à 80% masque des exclusions significatives. Le composant le plus critique (WalkForwardBacktester) n'est pas testé du tout.

**Effort total estimé pour atteindre la production-readiness : ~20h de travail réparties sur 2-3 semaines.**

---

*Rapport généré par 5 agents spécialisés — Architecture, Sécurité, DevOps, Testing/ML, Documentation*
*Date : 2026-03-12*
