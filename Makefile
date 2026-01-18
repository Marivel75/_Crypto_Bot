SHELL := /bin/bash
UV = uv
PYTHON = $(UV) run python
CLI_SCHEDULER = src.cli
LOAD_ENV := if [ -f .env ]; then set -a && . ./.env && set +a; fi

ARGS ?=
CONFIG ?= data/scheduler_config.json
PAIRS ?=
TIMEFRAMES ?=
EXCHANGE ?=
SCHEDULE_TIME ?=
SCHEDULER_ARGS_SCRIPT = ./scheduler_args.sh
SHOW_ARGS ?= 0

export CONFIG PAIRS TIMEFRAMES EXCHANGE SCHEDULE_TIME

# === RECURSIF ====

help: ## Show this help with available targets
	@echo "Available targets:"; \
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)


# ==== INSTALL AN CONFIGURATION ======

sync: ## Sync All Python Libraries
	$(UV) sync --group dev

browsers: ## Install Playwright Browser
	$(UV) run playwright install

precommit-install: ## Install pre-commit hooks
	$(UV) run pre-commit install

install: sync browsers precommit-install ## Sync and install pre-commit

pre-commit: ## Run the pre-commit
	$(UV) run pre-commit run --all-files

check: pre-commit test ## Run pre-commit and all tests


# ==== CLEAN THE STUFF =======

clean: ## Clean les fichiers temporaires
	find . -type d \( \
		-name "__pycache__" -o \
		-name ".pytest_cache" -o \
		-name ".mypy_cache" -o \
		-name ".ruff_cache" -o \
		-name "*.egg-info" \
	\) -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.Identifier' -exec rm -f {} + 2>/dev/null || true
	find . -type f -name '*:Zone.Identifier' -print0 | xargs -0 rm -f
	rm -f uv.lock
	@echo "✓ caches nettoyés (hors venv)"

clean-venv: ## Clean le venv
	find . -maxdepth 3 -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ environnements virtuels supprimés"


# ====== tests =======

test: ## Run all tests
	$(PYTHON) scripts/run_tests.py --type all $(ARGS)

test-unit: ## Run unit tests
	$(PYTHON) scripts/run_tests.py --type unit $(ARGS)

test-validation: ## Run data validation tests
	$(PYTHON) scripts/run_tests.py --type validation $(ARGS)

test-etl: ## Run ETL tests
	$(PYTHON) scripts/run_tests.py --type etl $(ARGS)

test-coverage: ## Run tests with coverage
	$(PYTHON) scripts/run_tests.py --type all --coverage $(ARGS)

test-report: ## Run tests with HTML coverage report
	$(PYTHON) scripts/run_tests.py --type all --coverage --report $(ARGS)


# ====== scheduler =======

validate-config: ## Validate scheduler arguments against config
	$(LOAD_ENV) && $(SCHEDULER_ARGS_SCRIPT) validate >/dev/null
	@if [ "$(SHOW_ARGS)" = "1" ]; then \
		echo "run args: $$($(SCHEDULER_ARGS_SCRIPT) run)"; \
		echo "schedule args: $$($(SCHEDULER_ARGS_SCRIPT) schedule)"; \
	fi

show-args: ## Print args computed from config (SHOW_ARGS=1)
	@$(MAKE) validate-config SHOW_ARGS=1

run: ## Run immediate collection (PAIRS=a,b TIMEFRAMES=1h,4h EXCHANGE=...)
	$(LOAD_ENV) && SCHED_ARGS="$$( $(SCHEDULER_ARGS_SCRIPT) run )" && \
		$(PYTHON) -m $(CLI_SCHEDULER) run $$SCHED_ARGS $(ARGS)

schedule: ## Run scheduler loop (SCHEDULE_TIME=09:00 EXCHANGE=...)
	$(LOAD_ENV) && SCHED_ARGS="$$( $(SCHEDULER_ARGS_SCRIPT) schedule )" && \
		$(PYTHON) -m $(CLI_SCHEDULER) schedule $$SCHED_ARGS $(ARGS)

run-binance: ## Run immediate collection on binance
	EXCHANGE=binance $(MAKE) run

run-kraken: ## Run immediate collection on kraken
	EXCHANGE=kraken $(MAKE) run

run-coinbase: ## Run immediate collection on coinbase
	EXCHANGE=coinbase $(MAKE) run

schedule-binance: ## Schedule collection on binance
	EXCHANGE=binance $(MAKE) schedule

schedule-kraken: ## Schedule collection on kraken
	EXCHANGE=kraken $(MAKE) schedule

schedule-coinbase: ## Schedule collection on coinbase
	EXCHANGE=coinbase $(MAKE) schedule
