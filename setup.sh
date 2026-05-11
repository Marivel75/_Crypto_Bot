#!/usr/bin/env bash
# Crypto Bot — Script d'installation automatique
# Détecte l'OS et installe les dépendances système + Python

set -e

# ── Couleurs ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║       Crypto Bot — Installation          ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Détection OS ─────────────────────────────────────────────────────────────
OS=$(uname -s 2>/dev/null || echo "Unknown")

case "$OS" in
  Darwin)
    PLATFORM="macos"
    ok "OS détecté : macOS"
    ;;
  Linux)
    PLATFORM="linux"
    ok "OS détecté : Linux"
    if   [ -f /etc/debian_version ];  then DISTRO="debian"
    elif [ -f /etc/redhat-release  ];  then DISTRO="redhat"
    elif [ -f /etc/arch-release    ];  then DISTRO="arch"
    elif [ -f /etc/alpine-release  ];  then DISTRO="alpine"
    else                                    DISTRO="unknown"
    fi
    echo "  Distribution : $DISTRO"
    ;;
  CYGWIN*|MINGW*|MSYS*)
    err "Windows détecté."
    echo "  Ce projet n'est pas supporté nativement sous Windows."
    echo "  Solutions :"
    echo "    - WSL2  : https://learn.microsoft.com/fr-fr/windows/wsl/install"
    echo "    - Docker: make docker  (aucune dépendance locale requise)"
    exit 1
    ;;
  *)
    PLATFORM="unknown"
    warn "OS non reconnu ($OS) — l'installation continue sans dépendances système."
    ;;
esac

# ── Dépendances système ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Dépendances système ──────────────────────────${NC}"

if [ "$PLATFORM" = "linux" ]; then
  case "$DISTRO" in
    debian)
      info "apt-get : python3-dev libpq-dev curl build-essential…"
      sudo apt-get update -qq
      sudo apt-get install -y --no-install-recommends \
        python3-dev libpq-dev curl build-essential > /dev/null
      ok "Dépendances installées (apt)"
      ;;
    redhat)
      info "yum : python3-devel postgresql-devel curl gcc…"
      sudo yum install -y python3-devel postgresql-devel curl gcc > /dev/null
      ok "Dépendances installées (yum)"
      ;;
    arch)
      info "pacman : python postgresql-libs curl base-devel…"
      sudo pacman -Sy --noconfirm python postgresql-libs curl base-devel > /dev/null
      ok "Dépendances installées (pacman)"
      ;;
    alpine)
      info "apk : python3-dev libpq-dev curl build-base…"
      sudo apk add --no-cache python3-dev libpq-dev curl build-base > /dev/null
      ok "Dépendances installées (apk)"
      ;;
    *)
      warn "Distribution non reconnue. Assurez-vous que libpq-dev et python3-dev sont installés."
      ;;
  esac

elif [ "$PLATFORM" = "macos" ]; then
  if command -v brew &>/dev/null; then
    if ! brew list libpq &>/dev/null 2>&1; then
      info "Homebrew : installation de libpq…"
      brew install libpq > /dev/null
      ok "libpq installé"
    else
      ok "libpq déjà présent"
    fi
  else
    warn "Homebrew non trouvé — si psycopg2-binary échoue, installez Homebrew puis relancez."
    warn "https://brew.sh"
  fi
fi

# ── Python ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Python ───────────────────────────────────────${NC}"

# Vérifie la version Python (3.10+ requis)
PYTHON=$(command -v python3 || command -v python || echo "")
if [ -z "$PYTHON" ]; then
  err "Python non trouvé. Installez Python 3.10 ou supérieur."
  exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  err "Python $PY_VERSION détecté — Python 3.10+ requis."
  exit 1
fi
ok "Python $PY_VERSION"

# Environnement virtuel (sauf si déjà dans conda ou venv)
IN_VENV=$($PYTHON -c "import sys; print('1' if sys.prefix != sys.base_prefix else '0')")
IN_CONDA=${CONDA_DEFAULT_ENV:-""}

if [ "$IN_VENV" = "1" ] || [ -n "$IN_CONDA" ]; then
  ok "Environnement virtuel actif : ${CONDA_DEFAULT_ENV:-venv}"
else
  if [ ! -d ".venv" ]; then
    info "Création de l'environnement virtuel (.venv)…"
    $PYTHON -m venv .venv
    ok "Environnement .venv créé"
  else
    ok "Environnement .venv existant"
  fi
  # Activer
  # shellcheck source=/dev/null
  source .venv/bin/activate
  ok "Environnement .venv activé"
fi

# ── Dépendances Python ────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Dépendances Python ───────────────────────────${NC}"
info "pip install -r requirements.txt…"
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "Toutes les dépendances installées"

# ── Configuration ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Configuration ────────────────────────────────${NC}"

if [ ! -f ".env" ]; then
  cp .env.example .env
  warn "Fichier .env créé depuis .env.example"
  echo "  → Éditez .env et renseignez vos clés API avant de lancer les collectes."
else
  ok "Fichier .env existant"
fi

# Dossiers requis
mkdir -p data/processed mlflow-artifacts
ok "Dossiers data/processed et mlflow-artifacts prêts"

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║        ✓ Installation terminée !         ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

if [ "$IN_VENV" = "0" ] && [ -z "$IN_CONDA" ] && [ -d ".venv" ]; then
  echo "  Activez l'environnement dans chaque nouveau terminal :"
  echo -e "    ${BOLD}source .venv/bin/activate${NC}"
  echo ""
fi

echo "  Prochaines étapes :"
echo "    1. Éditez .env avec vos clés API (Binance, etc.)"
echo "    2. make run        — API + Frontend"
echo "    3. make run-all    — API + MLflow + Frontend"
echo "    4. make docker     — stack complète (Docker)"
echo ""
