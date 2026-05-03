"""Alertes email pour les événements de collecte.

Configuration via variables d'environnement :
    ALERT_EMAIL_TO       — destinataire (obligatoire pour activer)
    ALERT_EMAIL_FROM     — expéditeur
    ALERT_EMAIL_PASSWORD — mot de passe app (Gmail : générer dans Sécurité du compte)
    ALERT_SMTP_HOST      — serveur SMTP (défaut : smtp.gmail.com)
    ALERT_SMTP_PORT      — port SMTP    (défaut : 587)

Si ALERT_EMAIL_TO est absent ou vide, toutes les fonctions sont des no-ops silencieux.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText

from logger_settings import logger

# Créateur — défini dans .env, jamais exposé en frontend
_CREATOR_EMAIL = os.getenv("ALERT_EMAIL_TO", "").strip()
_FROM = os.getenv("ALERT_EMAIL_FROM", "").strip()
_PWD  = os.getenv("ALERT_EMAIL_PASSWORD", "").strip()
_HOST = os.getenv("ALERT_SMTP_HOST", "smtp.gmail.com")
_PORT = int(os.getenv("ALERT_SMTP_PORT", "587"))


def _enabled() -> bool:
    return bool(_FROM and _PWD)


def _get_subscriber_emails() -> list[str]:
    """Récupère les emails des abonnés actifs depuis la DB."""
    try:
        from config.settings import config
        from sqlalchemy import create_engine, text
        db_url = config.get("database.url")
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT email FROM alert_subscribers WHERE active = 1")
            ).fetchall()
        return [row[0] for row in rows]
    except Exception as exc:
        logger.warning("Impossible de récupérer les abonnés (non-bloquant) : %s", exc)
        return []


def _recipients() -> list[str]:
    """Retourne la liste complète des destinataires : créateur + abonnés."""
    emails = _get_subscriber_emails()
    if _CREATOR_EMAIL and _CREATOR_EMAIL not in emails:
        emails = [_CREATOR_EMAIL] + emails
    return emails


def _send(subject: str, body: str) -> None:
    if not _enabled():
        return
    recipients = _recipients()
    if not recipients:
        return
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(_HOST, _PORT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(_FROM, _PWD)
            for to in recipients:
                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = subject
                msg["From"]    = _FROM
                msg["To"]      = to
                server.sendmail(_FROM, to, msg.as_string())
        logger.info("Alerte email envoyée à %d destinataire(s) : %s", len(recipients), subject)
    except Exception as exc:
        logger.warning("Alerte email non envoyée (non-bloquant) : %s", exc)


def notify_collect_start(exchanges: list[str], trigger: str = "planifié") -> None:
    """Envoie une alerte au démarrage de la collecte."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _send(
        subject=f"[Crypto Bot] Collecte démarrée — {now}",
        body=(
            f"La collecte vient de démarrer.\n\n"
            f"Déclenchement   : {trigger}\n"
            f"Heure           : {now}\n"
            f"Exchanges       : {', '.join(exchanges)}\n"
        ),
    )


def notify_collect_end(exchanges: list[str], n_stored: int, duration_s: float) -> None:
    """Envoie une alerte à la fin de la collecte."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    minutes, seconds = divmod(int(duration_s), 60)
    duration_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
    _send(
        subject=f"[Crypto Bot] Collecte terminée — {now}",
        body=(
            f"La collecte quotidienne est terminée.\n\n"
            f"Exchanges       : {', '.join(exchanges)}\n"
            f"Bougies stockées: {n_stored}\n"
            f"Durée           : {duration_str}\n"
            f"Fin             : {now}\n"
        ),
    )


def notify_collect_error(error: str) -> None:
    """Envoie une alerte en cas d'erreur critique lors de la collecte."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _send(
        subject=f"[Crypto Bot] ⚠️ Erreur collecte — {now}",
        body=(
            f"Une erreur s'est produite pendant la collecte quotidienne.\n\n"
            f"Heure  : {now}\n"
            f"Erreur : {error}\n"
        ),
    )
