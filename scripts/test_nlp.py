#!/usr/bin/env python3
"""Script de test du pipeline NLP : text mining, collecte news enrichie, affichage.

Usage:
    python scripts/test_nlp.py               # test text mining + collecte live
    python scripts/test_nlp.py --offline     # test text mining uniquement (pas de réseau)
    python scripts/test_nlp.py --db          # affiche les articles déjà en base
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

from src.ml.nlp.text_mining import analyse_text, extract_entities, detect_topics, extract_keywords

# ── Couleurs terminal ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

TOPIC_COLORS = {
    "regulation":    "\033[95m",
    "hack_security": "\033[91m",
    "adoption":      "\033[92m",
    "defi":          "\033[94m",
    "nft":           "\033[35m",
    "macro":         "\033[33m",
    "price_action":  "\033[93m",
    "general":       "\033[90m",
}


def _topic_str(topics: list[str]) -> str:
    parts = []
    for t in topics:
        c = TOPIC_COLORS.get(t, RESET)
        parts.append(f"{c}[{t.replace('_', ' ')}]{RESET}")
    return " ".join(parts)


def _sym_str(symbols: list[str]) -> str:
    return " ".join(f"{CYAN}{s}{RESET}" for s in symbols)


# ── 1. Test text mining sur exemples statiques ────────────────────────────────

SAMPLE_HEADLINES = [
    "Bitcoin ETF approved by SEC as Ethereum hits new ATH on Binance",
    "Solana DeFi protocol hacked, $50M stolen from liquidity pool",
    "Dogecoin and SHIB surge 30% amid Elon Musk tweets, Coinbase lists PEPE",
    "Fed raises interest rates, Bitcoin crashes 15% in macro selloff",
    "XRP lawsuit dismissed, Ripple partners with major banks for USDC adoption",
    "Cardano staking rewards increase as ADA community votes on protocol upgrade",
    "TON network integrates with Telegram, SUI and HYPE tokens rally 20%",
]


def test_text_mining():
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  1. TEXT MINING — exemples statiques{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

    for headline in SAMPLE_HEADLINES:
        result = analyse_text(headline)
        symbols = result["entities"]["crypto_symbols"]
        exchanges = result["entities"]["exchanges"]
        topics = result["topics"]
        keywords = result["keywords"][:4]

        print(f"\n{BOLD}  {headline[:70]}{RESET}")
        print(f"    Topics    : {_topic_str(topics)}")
        print(f"    Cryptos   : {_sym_str(symbols) if symbols else '—'}")
        if exchanges:
            print(f"    Exchanges : {', '.join(exchanges)}")
        print(f"    Keywords  : {', '.join(keywords)}")


# ── 2. Collecte live + enrichissement ────────────────────────────────────────

def test_live_collection():
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  2. COLLECTE LIVE — RSS feeds{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

    from api.dependencies import SessionLocal, engine
    from src.collectors.news_collector import NewsCollector
    from src.models.news import Base as NewsBase

    NewsBase.metadata.create_all(bind=engine)

    # Migration colonnes si nécessaire
    from sqlalchemy import text as sqlt
    with engine.connect() as conn:
        for col in [("entities", "JSON"), ("topics", "JSON")]:
            try:
                conn.execute(sqlt(f"ALTER TABLE news_articles ADD COLUMN {col[0]} {col[1]}"))
                conn.commit()
            except Exception:
                pass

    db = SessionLocal()
    try:
        with NewsCollector() as collector:
            print("  Collecte en cours (3 sources RSS)…")
            result = collector.fetch_and_store(db)

        print(f"\n  {GREEN}Stockés : {result['stored']}{RESET}  |  "
              f"Ignorés (doublons) : {result['skipped']}")

        if result["stored"] > 0:
            _show_recent_articles(db, limit=5)
    finally:
        db.close()


# ── 3. Affichage articles en base ─────────────────────────────────────────────

def test_db_articles():
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  3. ARTICLES EN BASE — derniers enrichis{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

    from api.dependencies import SessionLocal
    db = SessionLocal()
    try:
        _show_recent_articles(db, limit=10)
    finally:
        db.close()


def _show_recent_articles(db, limit: int = 5):
    from src.models.news import NewsArticle

    articles = (
        db.query(NewsArticle)
        .order_by(NewsArticle.collected_at.desc())
        .limit(limit)
        .all()
    )

    if not articles:
        print(f"  {YELLOW}Aucun article en base.{RESET}")
        return

    topic_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}

    print()
    for art in articles:
        topics = art.topics or ["general"]
        entities = art.entities or {}
        symbols = entities.get("crypto_symbols", [])
        label = art.sentiment_label or "neutral"
        score = art.sentiment_score

        label_color = GREEN if label == "positive" else RED if label == "negative" else "\033[90m"
        score_str = f"{score:+.2f}" if score is not None else "—"

        print(f"  {BOLD}{art.title[:75]}{RESET}")
        print(f"    Source : {art.source} | Sentiment : {label_color}{label} ({score_str}){RESET}")
        print(f"    Topics : {_topic_str(topics)}")
        print(f"    Cryptos: {_sym_str(symbols) if symbols else '—'}")
        print()

        for t in topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        for s in symbols:
            symbol_counts[s] = symbol_counts.get(s, 0) + 1

    # Résumé
    print(f"{BOLD}  Répartition topics :{RESET}")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        bar = "█" * count
        c = TOPIC_COLORS.get(topic, RESET)
        print(f"    {c}{topic:<15}{RESET} {bar} ({count})")

    if symbol_counts:
        print(f"\n{BOLD}  Cryptos mentionnées :{RESET}")
        for sym, count in sorted(symbol_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    {CYAN}{sym:<6}{RESET} × {count}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test pipeline NLP crypto")
    parser.add_argument("--offline", action="store_true",
                        help="Test text mining uniquement, sans réseau ni DB")
    parser.add_argument("--db", action="store_true",
                        help="Affiche uniquement les articles déjà en base")
    args = parser.parse_args()

    test_text_mining()

    if args.offline:
        print(f"\n{GREEN}Mode offline — tests text mining terminés.{RESET}\n")
        return

    if args.db:
        test_db_articles()
    else:
        test_live_collection()

    print(f"\n{GREEN}Tests terminés.{RESET}\n")


if __name__ == "__main__":
    main()
