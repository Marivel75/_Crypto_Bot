#!/usr/bin/env python3
"""Test du système d'alertes email.

Usage:
    python scripts/test_alerts.py           # envoie les 3 types d'alertes
    python scripts/test_alerts.py --config  # affiche la config sans envoyer
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from src.notifications.notifier import (
    _enabled, _CREATOR_EMAIL, _FROM, _HOST, _PORT,
    _get_subscriber_emails, _recipients,
    notify_collect_start, notify_collect_end, notify_collect_error,
)

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def show_config():
    print(f"\n{BOLD}Configuration alertes{RESET}")
    print(f"  SMTP         : {_HOST}:{_PORT}")
    print(f"  Expéditeur   : {_FROM or '(non défini)'}")
    print(f"  Créateur     : {_CREATOR_EMAIL or '(non défini)'}")
    print(f"  Actif        : {GREEN + 'OUI' if _enabled() else RED + 'NON (FROM ou PASSWORD manquant)'}{RESET}")

    subs = _get_subscriber_emails()
    print(f"  Abonnés DB   : {len(subs)}")
    for e in subs:
        print(f"    · {e}")

    all_recipients = _recipients()
    print(f"  Destinataires: {len(all_recipients)}")
    for e in all_recipients:
        print(f"    · {e}")
    print()


def run_tests():
    print(f"\n{BOLD}Test 1 — Alerte démarrage collecte (manuel){RESET}")
    notify_collect_start(["binance", "kraken"], trigger="manuel")
    print(f"  {GREEN}Envoyé (ou ignoré si config manquante){RESET}")

    print(f"\n{BOLD}Test 2 — Alerte fin de collecte{RESET}")
    notify_collect_end(["binance", "kraken"], n_stored=842, duration_s=37)
    print(f"  {GREEN}Envoyé{RESET}")

    print(f"\n{BOLD}Test 3 — Alerte erreur{RESET}")
    notify_collect_error("Connection timeout sur binance après 3 tentatives")
    print(f"  {GREEN}Envoyé{RESET}")

    print(f"\n{GREEN}Tests terminés. Vérifiez votre boîte mail.{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="store_true", help="Affiche la config sans envoyer")
    args = parser.parse_args()

    show_config()
    if not args.config:
        if not _enabled():
            print(f"{RED}Alertes désactivées — vérifiez ALERT_EMAIL_FROM et ALERT_EMAIL_PASSWORD dans .env{RESET}\n")
            sys.exit(1)
        run_tests()
