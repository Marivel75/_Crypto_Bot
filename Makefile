# Crypto Bot — Makefile
# ============================================================

.PHONY: run stop \
        docker docker-stop docker-logs \
        news history collect collect-schedule ticker collect-live \
        tests test-api test-paper test-cov \
        help

# ── Variables overridables ────────────────────────────────────
EXCHANGES ?= binance
RUNTIME   ?= 120

# ── Local (sans Docker) ───────────────────────────────────────

run:
	@echo "→ Démarrage de l'API FastAPI (port 8000)…"
	@uvicorn api.main:app --host 0.0.0.0 --port 8000 &
	@echo "→ Démarrage du frontend Streamlit (port 8501)…"
	@echo "  API  : http://localhost:8000/docs"
	@echo "  Front: http://localhost:8501"
	@echo "  (Ctrl+C pour arrêter Streamlit — 'make stop' pour l'API)"
	@streamlit run frontend/app.py

stop:
	@echo "→ Arrêt de l'API FastAPI…"
	@pkill -f "uvicorn api.main:app" 2>/dev/null && echo "  API arrêtée." || echo "  API déjà arrêtée."

# ── Docker ────────────────────────────────────────────────────

docker:
	@echo "→ Démarrage de la stack Docker (API + Frontend + MLflow)…"
	@echo "  API    : http://localhost:8000/docs"
	@echo "  Front  : http://localhost:8501"
	@echo "  MLflow : http://localhost:5001"
	@docker compose up --build

docker-stop:
	@docker compose down

docker-logs:
	@docker compose logs -f

# ── Données ───────────────────────────────────────────────────

news:
	@python scripts/collect_news.py --once

history:
	@python scripts/fetch_history.py

collect:
	@echo "→ Collecte OHLCV incrémentale — exchanges : $(EXCHANGES)"
	@python main.py --exchanges $(EXCHANGES)

collect-schedule:
	@echo "→ Collecte OHLCV planifiée (quotidienne 09:00) — exchanges : $(EXCHANGES)"
	@python main.py --schedule --exchanges $(EXCHANGES)

ticker:
	@echo "→ Ticker temps réel — exchanges : $(EXCHANGES)  durée : $(RUNTIME)s"
	@python main.py --ticker --exchanges $(EXCHANGES) --runtime $(RUNTIME)

collect-live:
	@echo "→ Collecte incrémentale + Ticker en parallèle — exchanges : $(EXCHANGES)"
	@python main.py --exchanges $(EXCHANGES) &
	@python main.py --ticker --exchanges $(EXCHANGES) --runtime $(RUNTIME)

# ── Tests ─────────────────────────────────────────────────────

tests:
	@python -m pytest tests/ -v

test-api:
	@python -m pytest tests/test_api.py -v

test-paper:
	@python -m pytest tests/test_paper_trading.py -v

test-cov:
	@python -m pytest tests/ --cov=src --cov=api --cov-report=term-missing

# ── Aide ──────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Crypto Bot — commandes disponibles"
	@echo "  ════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  LOCAL (sans Docker)"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make run                    Lance API (port 8000) + Streamlit (8501)"
	@echo "  make stop                   Arrête l'API FastAPI en arrière-plan"
	@echo ""
	@echo "  DOCKER"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make docker                 Lance la stack complète (API + Front + MLflow)"
	@echo "  make docker-stop            Arrête tous les conteneurs"
	@echo "  make docker-logs            Affiche les logs en temps réel"
	@echo ""
	@echo "  DONNÉES"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make collect                Collecte OHLCV incrémentale (binance)"
	@echo "  make collect EXCHANGES='binance kraken'   Plusieurs exchanges"
	@echo "  make collect-schedule       Collecte planifiée quotidienne (09:00)"
	@echo "  make ticker                 Ticker temps réel (binance, 120s)"
	@echo "  make ticker EXCHANGES='binance coinbase' RUNTIME=300"
	@echo "  make collect-live           OHLCV incrémental + ticker en parallèle"
	@echo "  make collect-live EXCHANGES='binance kraken' RUNTIME=300"
	@echo "  make news                   Collecte des news RSS (une passe)"
	@echo "  make history                Collecte l'historique OHLCV complet"
	@echo ""
	@echo "  TESTS"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make tests                  Tous les tests (verbose)"
	@echo "  make test-api               Tests des endpoints API uniquement"
	@echo "  make test-paper             Tests du module paper trading uniquement"
	@echo "  make test-cov               Tous les tests + rapport de couverture"
	@echo ""
