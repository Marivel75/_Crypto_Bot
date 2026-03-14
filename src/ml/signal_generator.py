"""Signal generator — orchestrates rule engine + optional ML predictor.

Produces :class:`~src.shared.models.signal.TradingSignal` objects and
persists them to the ``trading_signals`` table.

Only signals whose ``confidence_score`` meets or exceeds
:data:`~src.shared.constants.SIGNAL_CONFIDENCE_THRESHOLD` (0.6) are emitted.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Literal, Protocol, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD
from src.shared.db_models import TradingSignalOrm
from src.shared.models.signal import TradingSignal

logger = logging.getLogger(__name__)

# Model version tag applied when the ML predictor is unavailable.
_RULES_MODEL_VERSION = "rules_v1"
_ML_MODEL_VERSION = "xgboost_v2"


class RuleEngine(Protocol):
    """Minimal interface a rule engine must satisfy."""

    def evaluate(
        self,
        symbol: str,
        indicators: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a raw signal dict: direction, confidence, rules_triggered, timeframe."""
        ...


class Predictor(Protocol):
    """Minimal interface an ML predictor must satisfy."""

    def predict(self, features: Any) -> list[dict[str, Any]]:
        """Return a list of prediction dicts (direction, confidence, source)."""
        ...


class SignalGenerator:
    """Orchestrate rule engine and optional ML predictor to emit trading signals.

    When both a rule engine and a predictor are provided, ML confidence is
    blended with the rule-based confidence using a 60/40 weighting (ML/rules).
    If the predictor is absent or fails, the rule engine alone drives the signal.

    Args:
        rule_engine: Object implementing :class:`RuleEngine`.
        predictor: Optional object implementing :class:`Predictor`.  When
            ``None``, the generator operates in rules-only mode.
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        predictor: Predictor | None = None,
    ) -> None:
        self._rules = rule_engine
        self._predictor = predictor
        mode = "rules+ML" if predictor is not None else "rules-only"
        logger.info("SignalGenerator initialised in %s mode", mode)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        symbol: str,
        indicators: dict[str, Any],
        news_sentiment: float | None = None,
    ) -> TradingSignal | None:
        """Generate a trading signal for the given symbol.

        The pipeline is:
        1. Evaluate rule engine → base confidence + direction.
        2. If predictor is available, blend ML confidence (60%) with rule
           confidence (40%).
        3. Adjust confidence by news sentiment (±5 pp, capped at 0.95).
        4. Emit signal only if final confidence >= 0.6.

        Args:
            symbol: Trading pair symbol, e.g. ``"BTCUSDT"``.
            indicators: Dict of indicator values keyed by indicator name or
                        timeframe.  Passed directly to the rule engine.
            news_sentiment: Optional float in [-1.0, 1.0] representing
                            the aggregated news sentiment score.

        Returns:
            A :class:`TradingSignal` if confidence >= threshold, else ``None``.
        """
        rule_result = self._evaluate_rules(symbol, indicators)
        if rule_result is None:
            return None

        direction: str = rule_result["direction"]
        confidence: float = rule_result["confidence"]
        rules_triggered: list[str] = rule_result.get("rules_triggered", [])
        timeframe: str = rule_result.get("timeframe", "4h")
        timeframes_aligned: dict[str, Any] = rule_result.get("timeframes_aligned", {})

        model_version = _RULES_MODEL_VERSION

        # Blend with ML prediction if available
        if self._predictor is not None:
            ml_result = self._ml_predict(indicators)
            if ml_result is not None:
                ml_direction = ml_result["direction"]
                ml_confidence = float(ml_result["confidence"])

                if ml_direction == direction:
                    confidence = 0.6 * ml_confidence + 0.4 * confidence
                else:
                    # Conflicting signals — penalise confidence
                    confidence = 0.4 * min(ml_confidence, confidence)
                    logger.debug(
                        "Conflicting ML/rules direction for %s — confidence penalised",
                        symbol,
                    )
                model_version = _ML_MODEL_VERSION

        # Incorporate news sentiment (±5 pp)
        if news_sentiment is not None:
            sentiment_adj = float(news_sentiment) * 0.05
            if direction == "BUY":
                confidence += sentiment_adj
            else:
                confidence -= sentiment_adj
            confidence = max(0.0, min(0.95, confidence))

        confidence_decimal = Decimal(str(round(confidence, 4)))

        if confidence_decimal < SIGNAL_CONFIDENCE_THRESHOLD:
            logger.debug(
                "Signal for %s suppressed: confidence %.4f < %.2f",
                symbol,
                confidence,
                SIGNAL_CONFIDENCE_THRESHOLD,
            )
            return None

        leverage = self._suggest_leverage(confidence_decimal)
        fees = self._estimate_fees(leverage)
        margin = self._compute_margin_safety(leverage)

        # Suppress signal if cumulative fees exceed expected gain (doc §5.5)
        if not self._verify_fees(confidence_decimal, fees):
            logger.info(
                "Signal for %s suppressed: fees %.4f exceed expected gain at conf %.4f",
                symbol,
                fees,
                confidence_decimal,
            )
            return None

        signal = TradingSignal(
            symbol=symbol,
            signal_type=cast("Literal['BUY', 'SELL', 'HOLD']", direction),
            confidence_score=confidence_decimal,
            timeframe_primary=timeframe,
            timeframes_aligned=timeframes_aligned,
            rules_triggered=rules_triggered,
            leverage_suggested=leverage,
            margin_safety=margin,
            fees_estimated=fees,
            model_version=model_version,
        )

        logger.info(
            "Signal emitted: %s %s conf=%.4f model=%s rules=%s",
            symbol,
            direction,
            confidence,
            model_version,
            rules_triggered,
        )
        return signal

    async def save_signal(
        self,
        session: AsyncSession,
        signal: TradingSignal,
    ) -> None:
        """Persist a :class:`TradingSignal` to the ``trading_signals`` table.

        Args:
            session: Active SQLAlchemy async session.
            signal: The signal to persist.
        """
        orm = TradingSignalOrm(
            id=uuid.uuid4(),
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence_score=signal.confidence_score,
            timeframe_primary=signal.timeframe_primary,
            timeframes_aligned=signal.timeframes_aligned,
            rules_triggered=signal.rules_triggered,
            leverage_suggested=signal.leverage_suggested,
            margin_safety=signal.margin_safety,
            fees_estimated=signal.fees_estimated,
            model_version=signal.model_version,
        )
        session.add(orm)
        await session.flush()
        logger.info(
            "Signal persisted: id=%s symbol=%s type=%s conf=%s",
            orm.id,
            signal.symbol,
            signal.signal_type,
            signal.confidence_score,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_rules(
        self,
        symbol: str,
        indicators: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Call the rule engine and normalise its output.

        Args:
            symbol: Trading symbol.
            indicators: Indicator dict forwarded to the rule engine.

        Returns:
            Normalised dict with keys ``direction``, ``confidence``,
            ``rules_triggered``, ``timeframe``, ``timeframes_aligned``;
            or ``None`` if the rule engine fails.
        """
        try:
            result: dict[str, Any] = self._rules.evaluate(symbol, indicators)
        except Exception as exc:
            logger.error("Rule engine evaluation failed for %s: %s", symbol, exc)
            return None

        direction = str(result.get("direction", "HOLD")).upper()
        if direction not in {"BUY", "SELL", "HOLD"}:
            logger.warning("Unexpected direction %r from rule engine — defaulting HOLD", direction)
            direction = "HOLD"

        if direction == "HOLD":
            # HOLD signals are not emitted
            return None

        confidence = float(result.get("confidence", 0.0))
        return {
            "direction": direction,
            "confidence": min(max(confidence, 0.0), 1.0),
            "rules_triggered": result.get("rules_triggered", []),
            "timeframe": result.get("timeframe", "4h"),
            "timeframes_aligned": result.get("timeframes_aligned", {}),
        }

    def _ml_predict(
        self,
        indicators: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Run the ML predictor on the current indicator state.

        Converts the flat indicators dict into a single-row DataFrame for the
        predictor and returns the first prediction result.

        Args:
            indicators: Indicator dict (flat key/value pairs).

        Returns:
            First prediction dict or ``None`` on any error.
        """
        import pandas as pd  # local import — optional ML dependency

        if self._predictor is None:
            raise RuntimeError("Predictor is not loaded; call load() before generating ML signals.")
        try:
            features = pd.DataFrame([indicators])
            preds = self._predictor.predict(features)
            if preds:
                return preds[0]
        except Exception as exc:
            logger.warning("ML predictor failed — using rules only: %s", exc)
        return None

    @staticmethod
    def _suggest_leverage(confidence: Decimal) -> int | None:
        """Suggest leverage based on confidence tier.

        Args:
            confidence: Signal confidence score.

        Returns:
            Suggested leverage (5, 10, or 20) or ``None`` if confidence is
            too low to recommend any leverage.
        """
        if confidence >= Decimal("0.85"):
            return 20
        if confidence >= Decimal("0.75"):
            return 10
        if confidence >= Decimal("0.65"):
            return 5
        return None

    @staticmethod
    def _estimate_fees(leverage: int | None) -> Decimal:
        """Estimate cumulative round-trip trading fees.

        Fees from doc: maker ~0.02%, taker ~0.05%, slippage 0.05-0.2%.
        Leverage does NOT change the fee/gain ratio (both scale equally),
        so we return the base fee as a fraction of notional.

        Args:
            leverage: Suggested leverage (unused — fee ratio is leverage-invariant).

        Returns:
            Estimated total fee as a Decimal fraction (e.g. 0.0017 = 0.17%).
        """
        maker = Decimal("0.0002")  # 0.02%
        taker = Decimal("0.0005")  # 0.05%
        slippage = Decimal("0.001")  # 0.10% (mid-range estimate)
        return maker + taker + slippage  # 0.17% round-trip

    @staticmethod
    def _compute_margin_safety(leverage: int | None) -> Decimal | None:
        """Compute required margin safety per the 2x rule.

        Doc: "toujours 2x la position en marge libre."
        - Leverage  5x -> box 10%  -> margin required = 20% (2x)
        - Leverage 10x -> box  5%  -> margin required = 10% (2x)
        - Leverage 20x -> box 2.5% -> margin required =  5% (2x)

        Args:
            leverage: Suggested leverage tier.

        Returns:
            Required margin as Decimal fraction, or ``None`` if no leverage.
        """
        if leverage is None:
            return None
        box = Decimal("1") / Decimal(str(leverage))
        safety_multiplier = Decimal("2")
        return box * safety_multiplier

    @staticmethod
    def _verify_fees(confidence: Decimal, fees: Decimal) -> bool:
        """Check that estimated fees do not exceed expected gain.

        The expected gain proxy is ``confidence * base_move``, where
        ``base_move`` is a conservative 1% expected price movement for
        a qualifying signal.  If fees >= 50% of expected gain, suppress.

        Args:
            confidence: Signal confidence score.
            fees: Estimated cumulative fees (from :meth:`_estimate_fees`).

        Returns:
            ``True`` if the signal should be emitted, ``False`` to suppress.
        """
        base_move = Decimal("0.01")  # 1% expected move
        expected_gain = confidence * base_move
        return fees < expected_gain * Decimal("0.5")


# ---------------------------------------------------------------------------
# Async batch pipeline — called by APScheduler job
# ---------------------------------------------------------------------------


async def generate_signals_for_symbols(
    symbols: list[str] | None = None,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """Run the full signal generation pipeline for all tracked symbols.

    Reads the latest multi-timeframe indicators from TimescaleDB, evaluates
    the rule engine, and writes qualifying signals (confidence >= 0.6) to
    the ``trading_signals`` table.

    This function is **idempotent**: calling it twice in the same candle
    interval produces duplicate rows — the APScheduler caller must ensure
    it fires no more frequently than the primary timeframe (4h).

    No automated trade execution takes place anywhere in this function.

    Args:
        symbols: Override the list of symbols to process.  Defaults to
            :data:`~src.shared.constants.TRACKED_SYMBOLS`.
        session: Optional existing ``AsyncSession``.  If ``None``, a new
            session is created from :data:`~src.shared.database.async_session_factory`.

    Returns:
        Dict mapping ``symbol`` -> number of signals emitted (0 or 1 per symbol).
    """
    from datetime import UTC, datetime

    from src.ml.repositories.timescale import (
        TimescaleIndicatorRepository,
        TimescaleSignalRepository,
    )
    from src.ml.rules.engine import RuleEngine as ConcreteRuleEngine
    from src.shared.constants import TRACKED_SYMBOLS
    from src.shared.database import async_session_factory

    target_symbols: list[str] = list(symbols or TRACKED_SYMBOLS)
    engine = ConcreteRuleEngine.from_yaml()
    generator = SignalGenerator(rule_engine=engine)  # type: ignore[arg-type]

    # Timeframes queried per symbol
    _multi_tf = ("1h", "2h", "3h", "4h", "1D", "1W", "1M")

    results: dict[str, int] = {}
    started_at = datetime.now(UTC)

    async def _process_symbol(
        symbol: str,
        ind_repo: TimescaleIndicatorRepository,
        sig_repo: TimescaleSignalRepository,
        sess: AsyncSession,
    ) -> int:
        indicators_single = await ind_repo.get_multi_timeframe(symbol, list(_multi_tf))
        non_none = {tf: ind for tf, ind in indicators_single.items() if ind is not None}
        if not non_none:
            logger.warning("No indicator data for %s — skipping", symbol)
            return 0

        # Rule engine expects dict[str, list[IndicatorRecord]], wrap single records
        indicators: dict[str, Any] = {tf: [ind] for tf, ind in non_none.items()}

        # Use engine.evaluate() + aggregate() directly (returns TradingSignal | None)
        rule_results = engine.evaluate(symbol, indicators)
        signal = engine.aggregate(rule_results, symbol)
        if signal is None:
            return 0

        await generator.save_signal(sess, signal)
        return 1

    async def _run(sess: AsyncSession) -> None:
        ind_repo = TimescaleIndicatorRepository(sess)
        sig_repo = TimescaleSignalRepository(sess)

        for symbol in target_symbols:
            try:
                count = await _process_symbol(symbol, ind_repo, sig_repo, sess)
                results[symbol] = count
            except Exception:
                logger.exception("Unexpected error generating signal for %s", symbol)
                results[symbol] = 0

    if session is not None:
        await _run(session)
    else:
        async with async_session_factory() as sess:
            await _run(sess)
            await sess.commit()

    elapsed = (datetime.now(UTC) - started_at).total_seconds()
    total_emitted = sum(results.values())
    logger.info(
        "Signal generation complete: %d/%d signals emitted in %.2fs",
        total_emitted,
        len(target_symbols),
        elapsed,
    )
    return results
