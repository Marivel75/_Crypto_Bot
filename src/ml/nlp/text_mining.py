"""Text mining : extraction de mots-clés, entités, topics pour les news crypto.
Utilise TF-IDF et CountVectorizer (scikit-learn).
"""

from __future__ import annotations

import logging
import re
import string
from typing import Any

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

logger = logging.getLogger(__name__)

_CRYPTO_STOPWORDS: frozenset[str] = frozenset(
    {
        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "crypto",
        "cryptocurrency",
        "blockchain",
        "token",
        "coin",
        "market",
        "price",
        "trading",
        "said",
        "also",
        "according",
        "new",
        "one",
        "two",
        "three",
    }
)


def _clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_keywords(text: str, top_n: int = 8) -> list[str]:
    """Extrait les top-N mots-clés d'un texte via TF-IDF."""
    if not text or not text.strip():
        return []
    cleaned = _clean(text)
    vectorizer = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words="english",
        min_df=1,
    )
    try:
        matrix = vectorizer.fit_transform([cleaned])
    except ValueError:
        return []

    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    scores = matrix.toarray()[0]
    ranked = sorted(
        (
            (term, score)
            for term, score in zip(feature_names, scores)
            if term not in _CRYPTO_STOPWORDS and score > 0
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    return [term for term, _ in ranked[:top_n]]


def count_term_frequencies(texts: list[str], top_n: int = 50) -> dict[str, int]:
    """Fréquences des termes sur un corpus (pour word cloud)."""
    if not texts:
        return {}
    cleaned = [_clean(t) for t in texts if t and t.strip()]
    if not cleaned:
        return {}
    vectorizer = CountVectorizer(max_features=top_n, stop_words="english", min_df=1)
    try:
        matrix = vectorizer.fit_transform(cleaned)
    except ValueError:
        return {}
    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    totals = matrix.toarray().sum(axis=0)
    return dict(
        sorted(zip(feature_names, totals.tolist()), key=lambda kv: kv[1], reverse=True)
    )


# ---------------------------------------------------------------------------
# Entités connues
# ---------------------------------------------------------------------------

_CRYPTO_SYMBOLS: frozenset[str] = frozenset(
    [
        # --- OHLCV collectés (BTC, ETH, BNB, SOL, ADA) ---
        "BTC", "ETH", "BNB", "SOL", "ADA",
        # --- Frontend tracked_symbols ---
        "XRP", "DOT", "AVAX", "MATIC", "LINK",
        # --- Cadrage projet ---
        "USDT", "USDC", "DOGE", "TRX", "ATOM",
        # --- Top cryptos CoinGecko (table top_crypto en DB) ---
        "AAVE", "BCH", "CRO", "DAI", "HBAR",
        "HYPE", "LTC", "NEAR", "PEPE", "SHIB",
        "SUI", "TAO", "TON", "UNI", "XLM",
        "XMR", "XRP", "ZEC",
        # --- Autres présents dans le code (roulio-dev + indicateurs) ---
        "ETC", "ALGO", "VET", "FTM",
    ]
)

_EXCHANGE_NAMES: frozenset[str] = frozenset(
    [
        "binance",
        "coinbase",
        "kraken",
        "bitfinex",
        "bybit",
        "okx",
        "huobi",
        "kucoin",
        "bitget",
        "mexc",
    ]
)

# ---------------------------------------------------------------------------
# Taxonomy de topics (premier match gagne ; "general" = catch-all)
# ---------------------------------------------------------------------------

_TOPIC_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "regulation",
        ["sec", "cftc", "regulation", "ban", "esma", "legal", "law", "compliance"],
    ),
    (
        "hack_security",
        ["hack", "exploit", "vulnerability", "breach", "stolen", "attack"],
    ),
    ("adoption", ["adoption", "institutional", "etf", "partnership", "integration"]),
    (
        "defi",
        ["defi", "yield", "liquidity", "pool", "amm", "lending", "staking", "protocol"],
    ),
    ("nft", ["nft", "non-fungible", "marketplace", "opensea", "metaverse", "gaming"]),
    (
        "macro",
        ["fed", "inflation", "interest rate", "recession", "gdp", "economy", "dollar"],
    ),
    (
        "price_action",
        ["ath", "all-time high", "rally", "crash", "dump", "pump", "correction"],
    ),
    ("general", []),
]


# Mapping noms complets → ticker (pour détecter "Bitcoin", "Ethereum"…)
_CRYPTO_NAME_MAP: dict[str, str] = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
    "binance coin": "BNB", "ripple": "XRP", "cardano": "ADA",
    "avalanche": "AVAX", "polkadot": "DOT", "dogecoin": "DOGE",
    "polygon": "MATIC", "chainlink": "LINK", "litecoin": "LTC",
    "tron": "TRX", "cosmos": "ATOM", "toncoin": "TON",
    "shiba inu": "SHIB", "uniswap": "UNI", "monero": "XMR",
    "stellar": "XLM", "near protocol": "NEAR", "sui": "SUI",
    "pepe": "PEPE", "hyperliquid": "HYPE", "tao": "TAO",
}


def extract_entities(text: str) -> dict[str, list[str]]:
    """Détecte les symboles crypto et exchanges mentionnés dans le texte."""
    upper = text.upper()
    lower = text.lower()

    # Détection par ticker (ex: BTC, ETH)
    found: set[str] = {sym for sym in _CRYPTO_SYMBOLS if re.search(rf"\b{sym}\b", upper)}

    # Détection par nom complet (ex: "Bitcoin" → "BTC"), avec word boundary
    for name, ticker in _CRYPTO_NAME_MAP.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            found.add(ticker)

    symbols = sorted(found)
    exchanges = sorted({ex for ex in _EXCHANGE_NAMES if ex in lower})
    return {"crypto_symbols": symbols, "exchanges": exchanges}


def detect_topics(text: str) -> list[str]:
    """Classe le texte par topic(s) via keywords. Retourne ["general"] si aucun match."""
    lower = text.lower()
    matched = [
        topic
        for topic, keywords in _TOPIC_KEYWORDS
        if topic != "general" and any(kw in lower for kw in keywords)
    ]
    return matched if matched else ["general"]


def analyse_text(text: str, top_keywords: int = 8) -> dict[str, Any]:
    """Pipeline complet sur un article : keywords + entités + topics."""
    return {
        "keywords": extract_keywords(text, top_n=top_keywords),
        "entities": extract_entities(text),
        "topics": detect_topics(text),
    }
