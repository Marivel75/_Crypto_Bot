# Crypto Bot — Makefile
# ============================================================

.PHONY: run run-all stop mlflow \
        docker docker-stop docker-logs \
        news history collect collect-schedule ticker collect-live \
        db-migrate db-check db-inspect \
        tests test-api test-paper test-cov \
        help

# ── Variables overridables ────────────────────────────────────
EXCHANGES ?= binance
RUNTIME   ?= 120

# ── Base de données ───────────────────────────────────────────
# DB=sqlite (défaut) ou DB=postgres
# Pour postgres, définir POSTGRES_URL dans .env ou dans l'environnement.
DB ?= sqlite

-include .env
export POSTGRES_URL

_SQLITE_URL = sqlite:///data/processed/crypto_data.db

ifeq ($(DB),postgres)
  ifeq ($(POSTGRES_URL),)
    $(error DB=postgres mais POSTGRES_URL est vide. Définir POSTGRES_URL dans .env ou l'environnement.)
  endif
  export CRYPTO_BOT_DB_URL=$(POSTGRES_URL)
else
  export CRYPTO_BOT_DB_URL=$(_SQLITE_URL)
endif

# ── Local (sans Docker) ───────────────────────────────────────

run:
	@pkill -f "uvicorn api.main:app" 2>/dev/null || true
	@echo "→ Base de données : $(if $(filter postgres,$(DB)),PostgreSQL ($(POSTGRES_URL)),SQLite)"
	@echo "→ Démarrage de l'API FastAPI (port 8000)…"
	@python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info & \
	_api_pid=$$! ; \
	echo "  Attente de l'API (max 30s)…" ; \
	_i=0 ; \
	until curl -s http://localhost:8000/health > /dev/null 2>&1; do \
	  sleep 1 ; _i=$$((_i+1)) ; \
	  if [ $$_i -ge 30 ]; then \
	    echo "❌  L'API n'a pas démarré après 30s — consultez les logs ci-dessus." ; \
	    echo "    Debug : python -m uvicorn api.main:app --host 0.0.0.0 --port 8000" ; \
	    kill $$_api_pid 2>/dev/null ; exit 1 ; \
	  fi ; \
	done && \
	echo "  API prête  : http://localhost:8000/docs" && \
	echo "  Front      : http://localhost:8501" && \
	echo "  (Ctrl+C pour arrêter Streamlit — 'make stop' pour l'API)" && \
	streamlit run frontend/app.py

stop:
	@echo "→ Arrêt de l'API FastAPI…"
	@pkill -f "uvicorn api.main:app" 2>/dev/null && echo "  API arrêtée." || echo "  API déjà arrêtée."

run-all:
	@pkill -f "uvicorn api.main:app" 2>/dev/null || true
	@pkill -f "mlflow server" 2>/dev/null || true
	@mkdir -p mlflow-artifacts
	@echo "→ Stack locale complète — DB : $(if $(filter postgres,$(DB)),PostgreSQL ($(POSTGRES_URL)),SQLite)"
	@mlflow server \
	  --host 0.0.0.0 --port 5001 \
	  --backend-store-uri sqlite:///mlflow-local.db \
	  --default-artifact-root ./mlflow-artifacts \
	  --allowed-hosts "*" >/dev/null & \
	_mlf=$$!; \
	MLFLOW_TRACKING_URI=http://localhost:5001 \
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info & \
	_api=$$!; \
	trap 'echo "  Arrêt des services…"; kill $$_mlf $$_api 2>/dev/null' EXIT INT TERM; \
	echo "  Attente MLflow…"; sleep 5; \
	echo "  Attente API (max 30s)…"; \
	_i=0; \
	until curl -s http://localhost:8000/health >/dev/null 2>&1; do \
	  sleep 1; _i=$$((_i+1)); \
	  if [ $$_i -ge 30 ]; then \
	    echo "❌  API non démarrée — vérifiez les logs ci-dessus."; \
	    echo "    Debug : python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"; \
	    exit 1; \
	  fi; \
	done && \
	echo "  API     : http://localhost:8000/docs" && \
	echo "  MLflow  : http://localhost:5001" && \
	echo "  Front   : http://localhost:8501" && \
	echo "  (Ctrl+C pour tout arrêter)" && \
	streamlit run frontend/app.py

mlflow:
	@echo "→ Démarrage MLflow (port 5001)…"
	@mkdir -p mlflow-artifacts
	@mlflow server \
	  --host 0.0.0.0 \
	  --port 5001 \
	  --backend-store-uri sqlite:///mlflow-local.db \
	  --default-artifact-root ./mlflow-artifacts \
	  --allowed-hosts "*"

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
	@echo "→ Collecte des news RSS — DB : $(DB)"
	@python scripts/collect_news.py --once

history:
	@python scripts/fetch_history.py

collect:
	@echo "→ Collecte OHLCV incrémentale — exchanges : $(EXCHANGES)  DB : $(DB)"
	@python main.py --exchanges $(EXCHANGES)

collect-schedule:
	@echo "→ Collecte OHLCV planifiée (quotidienne 09:00) — exchanges : $(EXCHANGES)  DB : $(DB)"
	@python main.py --schedule --exchanges $(EXCHANGES)

ticker:
	@echo "→ Ticker temps réel — exchanges : $(EXCHANGES)  durée : $(RUNTIME)s  DB : $(DB)"
	@python main.py --ticker --exchanges $(EXCHANGES) --runtime $(RUNTIME)

collect-live:
	@echo "→ Collecte incrémentale + Ticker en parallèle — exchanges : $(EXCHANGES)  DB : $(DB)"
	@python main.py --exchanges $(EXCHANGES) &
	@python main.py --ticker --exchanges $(EXCHANGES) --runtime $(RUNTIME)

# ── Base de données ───────────────────────────────────────────

db-migrate:
	@echo "→ Migration SQLite → PostgreSQL…"
	@python scripts/migrate_to_postgres.py

db-check:
	@python -c "from api.dependencies import engine; print('DB connectée :', engine.url)"

db-inspect:
	@echo "→ Inspection de la base de données (DB : $(DB))…"
	@python scripts/check_db.py

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
	@echo "  make run                    Lance API + Streamlit avec SQLite (défaut)"
	@echo "  make run DB=postgres        Lance API + Streamlit avec PostgreSQL"
	@echo "  make stop                   Arrête l'API FastAPI en arrière-plan"
	@echo ""
	@echo "  DOCKER"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make docker                 Lance la stack complète (API + Front + MLflow)"
	@echo "  make docker-stop            Arrête tous les conteneurs"
	@echo "  make docker-logs            Affiche les logs en temps réel"
	@echo ""
	@echo "  DONNÉES  (ajouter DB=postgres pour utiliser PostgreSQL)"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make collect                Collecte OHLCV incrémentale (binance)"
	@echo "  make collect EXCHANGES='binance kraken'   Plusieurs exchanges"
	@echo "  make collect-schedule       Collecte planifiée quotidienne (09:00)"
	@echo "  make ticker                 Ticker temps réel (binance, 120s)"
	@echo "  make ticker EXCHANGES='binance coinbase' RUNTIME=300"
	@echo "  make collect-live           OHLCV incrémental + ticker en parallèle"
	@echo "  make news                   Collecte des news RSS (une passe)"
	@echo "  make history                Collecte l'historique OHLCV complet"
	@echo ""
	@echo "  BASE DE DONNÉES"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make db-migrate             Migre les données SQLite → PostgreSQL"
	@echo "  make db-check               Vérifie la connexion à la base active"
	@echo "  make db-inspect             Inspecte le contenu de la base active"
	@echo "  make db-inspect DB=postgres Inspecte PostgreSQL"
	@echo ""
	@echo "  TESTS"
	@echo "  ────────────────────────────────────────────────────────────────"
	@echo "  make tests                  Tous les tests (verbose)"
	@echo "  make test-api               Tests des endpoints API uniquement"
	@echo "  make test-paper             Tests du module paper trading uniquement"
	@echo "  make test-cov               Tous les tests + rapport de couverture"
	@echo ""
	@echo "  PostgreSQL : définir POSTGRES_URL dans .env (voir .env.example)"
	@echo ""
