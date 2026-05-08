# Crypto Bot — Makefile
# ============================================================

.PHONY: run stop docker docker-stop docker-logs news history collect collect-schedule ticker collect-live tests help

# ── Lancement local (sans Docker) ────────────────────────────
# Lance l'API en arrière-plan et Streamlit au premier plan.
# Ctrl+C arrête Streamlit ; `make stop` arrête l'API.

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

# ── Lancement Docker (stack complète) ────────────────────────

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

# ── Collecte de données ───────────────────────────────────────
# Variables overridables :
#   EXCHANGES  — exchange(s) séparés par des espaces (défaut : binance)
#   RUNTIME    — durée du ticker en secondes           (défaut : 120)
#
# Exemples :
#   make collect EXCHANGES="binance kraken"
#   make ticker  EXCHANGES="binance coinbase" RUNTIME=300

EXCHANGES ?= binance
RUNTIME   ?= 120

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

# ── Aide ──────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Commandes disponibles :"
	@echo ""
	@echo "  Local (sans Docker)"
	@echo "    make run          Lance API (8000) + Streamlit (8501)"
	@echo "    make stop         Arrête l'API FastAPI en arrière-plan"
	@echo ""
	@echo "  Docker"
	@echo "    make docker       Lance la stack complète (API + Front + MLflow)"
	@echo "    make docker-stop  Arrête tous les conteneurs"
	@echo "    make docker-logs  Affiche les logs en temps réel"
	@echo ""
	@echo "  Données"
	@echo "    make collect                           Collecte OHLCV incrémentale (binance)"
	@echo "    make collect EXCHANGES='binance kraken' Plusieurs exchanges"
	@echo "    make collect-schedule                  Collecte planifiée quotidienne"
	@echo "    make ticker                            Ticker temps réel (binance, 120s)"
	@echo "    make ticker EXCHANGES='binance coinbase' RUNTIME=300"
	@echo "    make collect-live                      Collecte incrémentale + ticker en parallèle (binance, 120s)"
	@echo "    make collect-live EXCHANGES='binance kraken' RUNTIME=300"
	@echo "    make news                              Collecte des news RSS (une passe)"
	@echo "    make history                           Collecte l'historique OHLCV complet"
	@echo ""
	@echo "  Dev"
	@echo "    make tests        Lance tous les tests pytest"
	@echo ""
