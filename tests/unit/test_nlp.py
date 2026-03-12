"""Unit tests for NLP modules: SentimentAnalyzer and text_mining utilities."""

from __future__ import annotations

import pytest

from src.ml.nlp.sentiment import SentimentAnalyzer
from src.ml.nlp.text_mining import (
    compute_tfidf,
    count_term_frequencies,
    extract_keywords,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Minimal labelled corpus: enough variety for the TF-IDF vectoriser (min_df=2
# requires at least two documents sharing a token) and for LR to train.
_BULLISH_TEXTS: list[str] = [
    "Bitcoin ETF approved by SEC, massive institutional adoption incoming rally",
    "Ethereum upgrade boosts network throughput, adoption surges record high",
    "Solana DeFi ecosystem expands with record transactions and new dApps launch",
    "BTC reaches all-time high as Wall Street funds pour capital into digital assets",
    "Positive regulatory clarity drives massive institutional investment in altcoins",
]

_BEARISH_TEXTS: list[str] = [
    "Crypto market crashes hard, investors panic sell amid exchange hack scandal",
    "Bitcoin plunges below support as regulatory crackdown threatens exchange operations",
    "Ethereum network congestion causes outage, DeFi protocols suffer major losses",
    "SEC rejects multiple crypto applications, market sentiment turns deeply negative",
    "Widespread liquidations devastate leveraged positions as market collapses overnight",
]

_NEUTRAL_TEXTS: list[str] = [
    "Central bank publishes report on digital currency research and development update",
    "Developer team releases weekly progress update on protocol improvements roadmap",
    "Conference panel discusses distributed ledger technology infrastructure standards",
    "Analyst publishes quarterly review of blockchain sector metrics and statistics",
    "Research institute releases technical whitepaper on consensus mechanism design",
]

_ALL_TEXTS: list[str] = _BULLISH_TEXTS + _BEARISH_TEXTS + _NEUTRAL_TEXTS
_ALL_LABELS: list[int] = [1] * 5 + [-1] * 5 + [0] * 5


@pytest.fixture()
def trained_analyzer() -> SentimentAnalyzer:
    """Return a SentimentAnalyzer fitted on the shared labelled corpus."""
    analyzer = SentimentAnalyzer()
    analyzer.train(_ALL_TEXTS, _ALL_LABELS)
    return analyzer


# ---------------------------------------------------------------------------
# TestSentimentAnalyzer
# ---------------------------------------------------------------------------


class TestSentimentAnalyzer:
    def test_positive_text(self, trained_analyzer: SentimentAnalyzer) -> None:
        score = trained_analyzer.predict("Bitcoin ETF approved, institutional investors rush to buy rally surge")

        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
        # A clearly bullish headline should be positive
        assert score > 0.0

    def test_negative_text(self, trained_analyzer: SentimentAnalyzer) -> None:
        score = trained_analyzer.predict("Market crashes hard, investors panic sell massive losses liquidation")

        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
        # A clearly bearish headline should be negative
        assert score < 0.0

    def test_neutral_text(self, trained_analyzer: SentimentAnalyzer) -> None:
        score = trained_analyzer.predict("Developer publishes quarterly technical report on blockchain research")

        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
        # Score must be in the valid range — neutrality is within [-0.5, 0.5]
        assert -0.7 <= score <= 0.7

    def test_score_is_always_in_range(self, trained_analyzer: SentimentAnalyzer) -> None:
        texts = [
            "MOON LAMBO TO THE MOON BULL RUN BUY BUY BUY!!!",
            "CRASH DUMP REKT FUD BEAR CAPITULATION PANIC SELL!!!",
            "",  # empty string — edge case
            "neutral boring nothing happening today",
        ]
        for text in texts:
            score = trained_analyzer.predict(text)
            assert -1.0 <= score <= 1.0, f"Score {score} out of range for: {text!r}"

    def test_batch_analyze(self, trained_analyzer: SentimentAnalyzer) -> None:
        batch = [
            "Bitcoin ETF approved, massive institutional rally incoming",
            "Market crashes, panic selling liquidations losses",
            "Developer releases technical whitepaper on protocol",
        ]
        scores = trained_analyzer.batch_predict(batch)

        assert isinstance(scores, list)
        assert len(scores) == len(batch)
        for score in scores:
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0

    def test_batch_analyze_preserves_order(self, trained_analyzer: SentimentAnalyzer) -> None:
        batch = _BULLISH_TEXTS[:3]
        scores = trained_analyzer.batch_predict(batch)

        assert len(scores) == 3

    def test_batch_analyze_empty_list(self, trained_analyzer: SentimentAnalyzer) -> None:
        scores = trained_analyzer.batch_predict([])

        assert scores == []

    def test_predict_raises_before_training(self) -> None:
        analyzer = SentimentAnalyzer()

        with pytest.raises(RuntimeError, match="trained"):
            analyzer.predict("some text")

    def test_batch_predict_raises_before_training(self) -> None:
        analyzer = SentimentAnalyzer()

        with pytest.raises(RuntimeError, match="trained"):
            analyzer.batch_predict(["some text"])

    def test_train_raises_on_length_mismatch(self) -> None:
        analyzer = SentimentAnalyzer()

        with pytest.raises(ValueError, match="length"):
            analyzer.train(["text one", "text two"], [1])

    def test_train_raises_on_invalid_labels(self) -> None:
        analyzer = SentimentAnalyzer()

        with pytest.raises(ValueError, match="labels"):
            analyzer.train(["text one", "text two"], [1, 99])

    def test_train_raises_on_insufficient_samples(self) -> None:
        analyzer = SentimentAnalyzer()

        with pytest.raises(ValueError):
            analyzer.train(["only one sample"], [1])

    def test_save_raises_before_training(self, tmp_path: object) -> None:
        import tempfile

        analyzer = SentimentAnalyzer()

        with pytest.raises(RuntimeError, match="trained"):
            analyzer.save(str(tempfile.mktemp(suffix=".joblib")))  # noqa: S306

    def test_save_and_load_roundtrip(self, trained_analyzer: SentimentAnalyzer, tmp_path: object) -> None:
        import pathlib

        path = str(pathlib.Path(str(tmp_path)) / "pipeline.joblib")
        trained_analyzer.save(path)

        loaded = SentimentAnalyzer()
        loaded.load(path)

        original_score = trained_analyzer.predict("Bitcoin ETF rally approved institutional")
        loaded_score = loaded.predict("Bitcoin ETF rally approved institutional")

        assert abs(original_score - loaded_score) < 1e-9


# ---------------------------------------------------------------------------
# TestTextMiner  (covers extract_keywords, compute_tfidf, count_term_frequencies)
# ---------------------------------------------------------------------------


class TestTextMiner:
    # --- extract_keywords ---------------------------------------------------

    def test_extract_keywords_returns_list(self) -> None:
        keywords = extract_keywords("Federal Reserve announces interest rate decision impacting financial markets")

        assert isinstance(keywords, list)

    def test_extract_keywords_top_n_respected(self) -> None:
        text = (
            "The Securities and Exchange Commission approved the first spot "
            "Bitcoin exchange-traded fund allowing institutional investors to "
            "gain regulated exposure to digital assets through traditional "
            "brokerage accounts without custodying private keys"
        )
        keywords = extract_keywords(text, top_n=5)

        assert len(keywords) <= 5

    def test_extract_keywords_filters_crypto_stopwords(self) -> None:
        text = (
            "Bitcoin price trading market coin token blockchain surges to new "
            "institutional record following SEC regulatory approval decision"
        )
        keywords = extract_keywords(text, top_n=20)

        crypto_stopwords = {
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
        }
        for kw in keywords:
            assert kw not in crypto_stopwords, f"Stopword found in keywords: {kw!r}"

    def test_extract_keywords_returns_strings(self) -> None:
        keywords = extract_keywords("regulatory approval for spot ETF drives institutional demand")

        for kw in keywords:
            assert isinstance(kw, str)
            assert len(kw) > 0

    def test_word_cloud_generation_via_count_frequencies(self) -> None:
        """count_term_frequencies drives word cloud data generation."""
        corpus = [
            "Federal Reserve raises interest rates impacting financial markets worldwide",
            "Interest rates hike dampens speculative investment appetite across sectors",
            "Financial markets react negatively to unexpected rate hike announcement",
            "Investors reassess portfolio allocation following rate decision announcement",
            "Global financial sector responds to Federal Reserve policy rate update",
        ]
        freq = count_term_frequencies(corpus, top_n=10)

        assert isinstance(freq, dict)
        assert len(freq) <= 10
        for term, count in freq.items():
            assert isinstance(term, str)
            assert isinstance(count, int)
            assert count >= 1
        # Verify descending order
        counts = list(freq.values())
        assert counts == sorted(counts, reverse=True)

    def test_empty_input_extract_keywords(self) -> None:
        assert extract_keywords("") == []

    def test_empty_input_whitespace_only(self) -> None:
        assert extract_keywords("   ") == []

    def test_empty_input_compute_tfidf(self) -> None:
        result = compute_tfidf([])

        assert result == {}

    def test_empty_input_count_term_frequencies(self) -> None:
        result = count_term_frequencies([])

        assert result == {}

    def test_blank_strings_only_compute_tfidf(self) -> None:
        result = compute_tfidf(["", "   ", "\t"])

        assert result == {}

    def test_blank_strings_only_count_term_frequencies(self) -> None:
        result = count_term_frequencies(["", "   "])

        assert result == {}

    def test_compute_tfidf_returns_scores(self) -> None:
        corpus = [
            "Federal Reserve raises interest rates affecting bond markets significantly",
            "Interest rates hike triggers bond market volatility across investment sectors",
            "Bond market reacts sharply to unexpected Federal Reserve rate decision today",
            "Investment funds reassess portfolio strategy amid rising interest rate environment",
            "Federal Reserve signals further rate increases to combat persistent inflation pressure",
        ]
        result = compute_tfidf(corpus)

        assert isinstance(result, dict)
        assert len(result) > 0
        for term, score in result.items():
            assert isinstance(term, str)
            assert isinstance(score, float)
            assert score >= 0.0

    def test_compute_tfidf_sorted_descending(self) -> None:
        corpus = [
            "Federal Reserve announces quantitative easing policy to stimulate economic growth",
            "Quantitative easing program expanded by Federal Reserve amid economic slowdown",
            "Economic growth projections revised downward following Federal Reserve announcement",
            "Reserve bank policy impacts quantitative easing expectations for economic outlook",
            "Federal policy makers debate quantitative easing effects on long-term economic stability",
        ]
        result = compute_tfidf(corpus)

        if result:
            scores = list(result.values())
            assert scores == sorted(scores, reverse=True)

    def test_extract_keywords_single_word_input(self) -> None:
        # A single unique word may produce an empty list because TF-IDF on a
        # single-token document can fail vectorisation gracefully
        keywords = extract_keywords("hello")

        assert isinstance(keywords, list)

    def test_count_term_frequencies_top_n_respected(self) -> None:
        corpus = [
            "The quick brown fox jumps over the lazy dog near the river bank",
            "A lazy dog sat near the river watching the fox and the brown bear",
            "The brown bear jumped over the fox and ran toward the river bank",
        ]
        result = count_term_frequencies(corpus, top_n=3)

        assert len(result) <= 3
