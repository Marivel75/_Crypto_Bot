"""Text mining utilities: keyword extraction, entity detection, topic labelling, DB writes.

Uses TF-IDF and CountVectorizer from scikit-learn for keyword extraction.
Entity extraction uses regex patterns for crypto symbols and exchange names.
Topic detection is keyword-based (no external model required).
Results are persisted to the ``text_mining_results`` table via SQLAlchemy.
"""

from __future__ import annotations

import logging
import re
import string
import uuid
from datetime import UTC, datetime
from typing import Any

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db_models import TextMiningResultOrm

logger = logging.getLogger(__name__)

# Common stop words to strip from keyword lists (supplements sklearn's list).
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
    """Lowercase, strip punctuation and extra whitespace.

    Args:
        text: Raw input string.

    Returns:
        Cleaned text suitable for vectorisation.
    """
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)  # remove URLs
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract the top-N keywords from a single text using TF-IDF.

    Uses a single-document TF-IDF fit so that term frequency is weighted
    by the inverse of term length (sublinear_tf), making rare multi-word
    phrases score higher than high-frequency filler words.

    Args:
        text: Raw news article or headline.
        top_n: Number of keywords to return. Default 10.

    Returns:
        List of at most ``top_n`` keyword strings, ordered by TF-IDF score
        descending.
    """
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
        tfidf_matrix = vectorizer.fit_transform([cleaned])
    except ValueError as exc:
        logger.warning("extract_keywords: vectoriser failed on text (%s): %s", text[:60], exc)
        return []

    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    scores = tfidf_matrix.toarray()[0]

    # Pair (term, score) and filter out crypto stopwords
    ranked = sorted(
        (
            (term, score)
            for term, score in zip(feature_names, scores, strict=True)
            if term not in _CRYPTO_STOPWORDS and score > 0
        ),
        key=lambda x: x[1],
        reverse=True,
    )

    keywords = [term for term, _ in ranked[:top_n]]
    logger.debug("extract_keywords: top-%d from %d chars: %s", top_n, len(text), keywords)
    return keywords


def compute_tfidf(texts: list[str]) -> dict[str, float]:
    """Compute corpus-level TF-IDF scores for all terms across a set of texts.

    Useful for building a global vocabulary ranked by relevance across a
    collection of news articles.

    Args:
        texts: List of raw text documents (articles or headlines).

    Returns:
        Dict mapping each term to its mean TF-IDF score across all documents
        where it appears, sorted descending by score.  Empty dict if input
        is empty or all texts are blank.
    """
    if not texts:
        return {}

    cleaned = [_clean(t) for t in texts if t and t.strip()]
    if not cleaned:
        return {}

    vectorizer = TfidfVectorizer(
        max_features=5_000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words="english",
        min_df=2,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(cleaned)
    except ValueError as exc:
        logger.warning("compute_tfidf: vectoriser failed: %s", exc)
        return {}

    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    # Mean score across documents (ignoring zeros)
    arr = tfidf_matrix.toarray()
    mean_scores = arr.mean(axis=0)

    result: dict[str, float] = {
        term: float(score)
        for term, score in zip(feature_names, mean_scores, strict=True)
        if score > 0 and term not in _CRYPTO_STOPWORDS
    }

    # Return sorted by score descending
    sorted_result = dict(sorted(result.items(), key=lambda kv: kv[1], reverse=True))
    logger.info("compute_tfidf: %d terms computed from %d documents", len(sorted_result), len(cleaned))
    return sorted_result


def count_term_frequencies(texts: list[str], top_n: int = 50) -> dict[str, int]:
    """Return the top-N most frequent terms across a corpus using CountVectorizer.

    Args:
        texts: List of raw text documents.
        top_n: Maximum number of terms to return. Default 50.

    Returns:
        Dict mapping term to total count, sorted by count descending.
    """
    if not texts:
        return {}

    cleaned = [_clean(t) for t in texts if t and t.strip()]
    if not cleaned:
        return {}

    vectorizer = CountVectorizer(
        max_features=top_n,
        stop_words="english",
        ngram_range=(1, 1),
        min_df=1,
    )

    try:
        count_matrix = vectorizer.fit_transform(cleaned)
    except ValueError as exc:
        logger.warning("count_term_frequencies: vectoriser failed: %s", exc)
        return {}

    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()
    totals = count_matrix.toarray().sum(axis=0)

    result = dict(
        sorted(
            zip(feature_names, totals.tolist(), strict=True),
            key=lambda kv: kv[1],
            reverse=True,
        )
    )
    return result


# ---------------------------------------------------------------------------
# Known entity lists for basic named-entity recognition
# ---------------------------------------------------------------------------

_CRYPTO_SYMBOLS: frozenset[str] = frozenset(
    [
        "BTC",
        "ETH",
        "BNB",
        "XRP",
        "SOL",
        "ADA",
        "AVAX",
        "DOT",
        "DOGE",
        "TRX",
        "ATOM",
        "USDT",
        "USDC",
        "MATIC",
        "LINK",
        "LTC",
        "BCH",
        "XLM",
        "ETC",
        "ALGO",
        "VET",
        "FTM",
        "NEAR",
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
# Topic keyword taxonomy (first match wins; "general" is catch-all)
# ---------------------------------------------------------------------------

_TOPIC_KEYWORDS: list[tuple[str, list[str]]] = [
    ("regulation", ["sec", "cftc", "regulation", "ban", "esma", "legal", "law", "compliance"]),
    ("hack_security", ["hack", "exploit", "vulnerability", "breach", "stolen", "attack"]),
    ("adoption", ["adoption", "institutional", "etf", "partnership", "integration"]),
    ("defi", ["defi", "yield", "liquidity", "pool", "amm", "lending", "staking", "protocol"]),
    ("nft", ["nft", "non-fungible", "marketplace", "opensea", "metaverse", "gaming"]),
    ("macro", ["fed", "inflation", "interest rate", "recession", "gdp", "economy", "dollar"]),
    ("price_action", ["ath", "all-time high", "rally", "crash", "dump", "pump", "correction"]),
    ("general", []),
]


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract crypto symbols and exchange names from text using regex.

    Args:
        text: Raw article text (title + optional content).

    Returns:
        Dict with keys ``"crypto_symbols"`` and ``"exchanges"``, each a
        deduplicated sorted list of found entities.
    """
    upper_text = text.upper()
    lower_text = text.lower()

    found_symbols: list[str] = sorted({sym for sym in _CRYPTO_SYMBOLS if re.search(rf"\b{sym}\b", upper_text)})
    found_exchanges: list[str] = sorted({ex for ex in _EXCHANGE_NAMES if ex in lower_text})

    return {
        "crypto_symbols": found_symbols,
        "exchanges": found_exchanges,
    }


def detect_topics(text: str) -> list[str]:
    """Keyword-based topic labelling.

    Assigns one or more topic labels to the text.  The ``"general"``
    catch-all is assigned when no specific topic keyword matches.

    Args:
        text: Raw text to classify.

    Returns:
        List of topic label strings (e.g. ``["regulation", "macro"]``).
    """
    lower_text = text.lower()
    matched: list[str] = []

    for topic, keywords in _TOPIC_KEYWORDS:
        if topic == "general":
            continue
        if any(kw in lower_text for kw in keywords):
            matched.append(topic)

    if not matched:
        matched.append("general")

    return matched


def analyse_text(
    text: str,
    top_keywords: int = 15,
    top_words: int = 50,
) -> dict[str, Any]:
    """Run the full text-mining pipeline on a single document.

    Args:
        text: Raw text (title + optional content).
        top_keywords: Number of TF-IDF keywords to extract.
        top_words: Number of words for the word-cloud frequency map.

    Returns:
        Dict with keys:
        - ``word_cloud``: ``dict[str, int]`` word frequency map
        - ``keywords``: ``list[str]`` TF-IDF keywords
        - ``entities``: ``dict`` with ``crypto_symbols`` and ``exchanges``
        - ``topics``: ``list[str]`` topic labels
    """
    return {
        "word_cloud": count_term_frequencies([text], top_n=top_words),
        "keywords": extract_keywords(text, top_n=top_keywords),
        "entities": extract_entities(text),
        "topics": detect_topics(text),
    }


async def save_text_mining_result(
    session: AsyncSession,
    article_id: str,
    text: str,
    summary: str | None = None,
) -> TextMiningResultOrm:
    """Analyse ``text`` and persist the result to ``text_mining_results``.

    Args:
        session: Active async SQLAlchemy session (caller must commit).
        article_id: UUID string of the parent ``NewsArticleOrm``.
        text: Raw article text to analyse.
        summary: Optional pre-computed article summary.

    Returns:
        The persisted :class:`TextMiningResultOrm` instance (not yet committed).
    """
    result = analyse_text(text)

    orm = TextMiningResultOrm(
        id=uuid.uuid4(),
        article_id=article_id,
        word_cloud=result["word_cloud"],
        summary=summary,
        entities=result["entities"],
        topics=result["topics"],
        processed_at=datetime.now(UTC),
    )
    session.add(orm)
    await session.flush()

    logger.info(
        "Saved text_mining_result for article_id=%s topics=%s entities=%s",
        article_id,
        result["topics"],
        result["entities"],
    )
    return orm
