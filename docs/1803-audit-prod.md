# Audit Production CryptoBot — 18 mars 2026

**VPS:** 54.37.38.118 (OVH)
**Domaine:** dtsc-cryptobot.fr
**Branche:** feature/phase2-cadrage-completion
**Conformite cadrage:** 67%

---

## Infrastructure (9/10)

| Metrique | Valeur | Status |
|---|---|---|
| VPS | OVH 6 cores, 11 GB RAM, 96 GB disk | Sain |
| Uptime | 2 jours 11h | Stable |
| CPU | 0.36 load avg | Excellent |
| RAM | 6.8 GB libre (59%) | OK |
| Disk | 14 GB / 96 GB (15%) | Large |
| Docker | 12 containers, tous healthy | OK |
| SSL | Let's Encrypt, expire 5 juin 2026 (78j) | OK |
| Firewall | UFW actif, fail2ban 3 jails (sshd, nginx-auth, nginx-bots) | Securise |
| Docker Engine | 29.3.0 | OK |
| Docker Compose | v5.1.0 | OK |

---

## Services Docker (12/12 up)

| Service | CPU | RAM | Status |
|---|---|---|---|
| API (FastAPI) | 0.21% | 91 MB / 512 MB (18%) | Excellent |
| Frontend (Streamlit) | 0.54% | 216 MB / 512 MB (42%) | OK |
| ETL Worker | 0.00% | 342 MB / 512 MB (67%) | **DNS FAILURE** |
| ML Worker | actif | - | Signaux emis toutes les 15 min |
| TimescaleDB | 0.04% | 170 MB / 1 GB (17%) | 44 MB data |
| MLflow | 0.02% | 827 MB / 1 GB (81%) | OK mais 0 experiences |
| MinIO | 0.00% | 185 MB / 512 MB (36%) | 1.25 MB stocke |
| Prometheus | actif | - | 479 metriques, UP |
| Grafana | actif | - | UP, auth a verifier |
| Nginx | actif | - | Reverse proxy OK |
| postgres-exporter | actif | - | UP |
| node-exporter | actif | - | UP |
| cadvisor | actif | - | UP |
| **nginx-exporter** | **DOWN** | - | **Scrape echoue** |

---

## Pipeline de Donnees

| Donnee | Volume | Fraicheur | Status |
|---|---|---|---|
| OHLCV 1min | 79 000 records | 1 min | OK |
| OHLCV 1h | - | 55 min | Stale |
| OHLCV 1d | - | 20h | Stale |
| News (Decrypt) | 218 articles | 20 min | OK |
| News (Cointelegraph) | 356 articles | 35 min | OK |
| News (CryptoNews) | 114 articles | 20 min | OK |
| Indicateurs | 7 463 | 55 min | OK |
| Signaux | 2 290 | 3 min | Actif |
| Users | 3 | - | - |

---

## ML Pipeline

| Metrique | Valeur | Cible | Status |
|---|---|---|---|
| Signaux totaux | 2 290 (1 672 SELL, 618 BUY) | - | Actif |
| Confidence moyenne | 0.96 | >= 0.6 | Tres haute |
| Accuracy | **46.3%** | **60%+** | **SOUS-CIBLE** |
| Symboles actifs | 5/12 (BTC, ETH, BNB, XRP, USDC) | 12/12 | **7 manquants** |
| Symboles sans indicateurs | SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM | - | **Pas de signaux** |
| MLflow experiments | **0** | >= 1 | **Phase 2 ML pas demarree** |
| Signaux par symbole (top 5) | ETH 603, BNB 554, BTC 490, XRP 335, USDC 308 | - | - |

---

## Endpoints Publics

| Route | Code | Latence | Status |
|---|---|---|---|
| `/` (redirect) | 301 | 0.17s | OK |
| `/crypto/` (dashboard) | 200 | 0.15s | OK |
| `/health` | 200 | - | OK (DB connected) |
| `/api/v1/auth/login` | 422 | - | OK (validation sans body) |
| `/api/v1/system/sources-status` | 200 | - | OK |
| `/grafana/` | 302 | 0.12s | OK (redirect login) |
| `/x/` (proxy Anthropic) | 200 | - | OK |
| `/docs` (Swagger) | **404** | 0.14s | **Manquant** |
| `/api/v1/crypto/BTC` | **404** | - | **Route erreur** |
| `/api/v1/signals/` | **Erreur** | - | **JSON invalide** |
| `/api/v1/news/` | **Erreur** | - | **JSON invalide** |

---

## Monitoring

| Composant | Status | Detail |
|---|---|---|
| Prometheus | UP | 479 metriques, scrape API + postgres-exporter |
| Grafana | UP | Auth par defaut, dashboards a verifier |
| nginx-exporter | **DOWN** | Pas de metriques reverse proxy |
| node-exporter | UP | Metriques systeme (CPU, RAM, disk) |
| cadvisor | UP | Metriques containers Docker |
| Loki (logs) | **ABSENT** | Pas de centralisation logs |
| Tracing | **ABSENT** | Pas de correlation IDs |
| ETL metriques | **ABSENT** | Pas de /metrics sur ETL worker |
| ML metriques | **ABSENT** | Pas de /metrics sur ML worker |

---

## Securite (8/10)

### Points forts
- SSL/TLS Let's Encrypt avec HSTS preload
- Headers securite complets (X-Content-Type, X-Frame-Options, Referrer-Policy, Permissions-Policy)
- Ports internes (DB 5432, MinIO 9000, MLflow 5000) bind sur 127.0.0.1
- UFW actif, fail2ban 3 jails
- `.env` permissions 600, pas dans git

### Points a corriger
- **Exporters exposes sur 0.0.0.0** : ports 9187, 9100, 8080 accessibles depuis internet
- **Rate limiting partiel** : present sur `/api/v1/auth/` mais pas sur tous les endpoints
- **CSP header manquant** : Content-Security-Policy non configure
- **Proxy `/x/` et `/y/` sans auth** : n'importe qui peut proxyer l'API Anthropic via le serveur

---

## Tests (codebase local)

| Categorie | Nombre |
|---|---|
| Tests passes | 1 054 |
| Tests echoues | 2 (config defaults — CoinGecko key, OpenAI key) |
| Erreurs | 89 (dep `prometheus-fastapi-instrumentator` manquante) |
| Skipped | 9 |
| Fichiers test | 74 |
| Fichiers source | 101 |
| Duree | 2 min 45s |

---

## Codebase

| Metrique | Valeur |
|---|---|
| Branche | `feature/phase2-cadrage-completion` |
| Dernier commit | `5c5027e` chore(infra): migrate requirements.txt to pyproject.toml + uv |
| Package manager | uv 0.8.22 (168 packages resolus) |
| Coverage cible | 78% (pyproject.toml) |
| Fichiers non-committed | 9 (collectors on-chain, models paper trading) |

---

## 3 Problemes Critiques

### 1. ETL DNS Resolution Failure (BLOQUANT)
```
Network error contacting Binance: [Errno -2] Name or service not known
```
Le container ETL ne peut plus resoudre les DNS externes. Toutes les collectes API echouent apres 5 tentatives. Impact : donnees 1h/1d stale, 7 symboles sans indicateurs.

**Action** : verifier `/etc/resolv.conf` dans le container, Docker DNS config, regles UFW outbound.

### 2. Signal Accuracy 46.3% (cible 60%+)
Les regles Phase 1 (RSI, Bollinger, Harmonic, Trend) produisent des signaux avec 0.96 de confidence moyenne mais seulement 46.3% de precision reelle. Pire qu'un coin flip.

**Action** : tuner les seuils dans `config/indicators.yaml`, activer MLflow pour tracker les experiments.

### 3. 7 Symboles Sans Indicateurs
SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM n'ont pas d'indicateurs calcules. Le ML worker skip ces symboles.

**Action** : lie au probleme DNS (#1). Corriger le DNS restaurera la collecte pour ces symboles.

---

## Conformite Cadrage PDF (67%)

| Axe | Score |
|---|---|
| Fonctionnalites | 65% (7/11 features) |
| Stack technique | 72% |
| Contraintes techniques | 75% |
| Calendrier | 92% |
| Personas | 62% |
| Sources de veille | 40% (4/10 sources) |
| **GLOBAL** | **67%** |

### 8 Features Manquantes (33%)

| # | Feature | Priorite | Owner |
|---|---|---|---|
| F1 | Paper Trading (Hyperliquid perps) | P0 | Jules |
| F2 | Reinforcement Learning (SARSA, Q-Learning) | P0 | Mikael |
| F3 | Deep Learning LSTM (3 modeles 4h/1d/1w) | P1 | Mikael |
| F4 | Clustering non supervise (regime global + per-coin) | P1 | Mikael |
| F5 | Donnees on-chain (Mempool, Blockchain.com, Etherscan) | P1 | Jules |
| F6 | Systeme d'alertes (email, Telegram, in-app) | P0 | Jules |
| F7 | Sources reglementaires (ESMA, SEC, EU Blockchain) | P1 | Jules |
| F8 | Web scraping BeautifulSoup | P2 | Jules |

---

## Prochaines Actions (par priorite)

1. **Fix DNS ETL** — restaurer la collecte de donnees (bloquer #1)
2. **Fix nginx-exporter** — restaurer les metriques Nginx
3. **Bind exporters sur 127.0.0.1** — securiser ports 9187, 9100, 8080
4. **Tuner seuils signaux** — ameliorer accuracy de 46% vers 60%+
5. **Lancer BMAD Phase 2** — architecture validee, sprint planning, puis dev des 8 features
