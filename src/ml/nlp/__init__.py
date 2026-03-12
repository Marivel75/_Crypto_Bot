"""NLP sub-package: sentiment analysis and text mining."""

from __future__ import annotations

from src.ml.nlp.sentiment import SentimentAnalyzer
from src.ml.nlp.text_mining import (
    compute_tfidf,
    count_term_frequencies,
    extract_keywords,
)


# TextMiner is a namespace alias that groups the standalone text-mining
# functions for callers that prefer the class-style import pattern.
class TextMiner:
    """Thin façade over the text-mining pure functions.

    Provides a class-based API for keyword extraction, word-cloud generation,
    and corpus-level TF-IDF so that callers can depend on a single name.
    """

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10) -> list[str]:
        """Extract top-N TF-IDF keywords from a single text.

        Args:
            text: Raw news article or headline.
            top_n: Number of keywords to return. Default 10.

        Returns:
            List of at most ``top_n`` keyword strings ordered by relevance.
        """
        return extract_keywords(text, top_n=top_n)

    @staticmethod
    def generate_word_cloud(texts: list[str], top_n: int = 50) -> dict[str, int]:
        """Return top-N term frequencies across a corpus.

        Args:
            texts: List of raw text documents.
            top_n: Maximum number of terms to return. Default 50.

        Returns:
            Dict mapping term to total count, sorted by count descending.
        """
        return count_term_frequencies(texts, top_n=top_n)

    @staticmethod
    def compute_tfidf(texts: list[str]) -> dict[str, float]:
        """Compute corpus-level TF-IDF scores for all terms.

        Args:
            texts: List of raw text documents (articles or headlines).

        Returns:
            Dict mapping each term to its mean TF-IDF score, sorted descending.
        """
        return compute_tfidf(texts)


__all__ = [
    "SentimentAnalyzer",
    "TextMiner",
    "compute_tfidf",
    "count_term_frequencies",
    "extract_keywords",
]
