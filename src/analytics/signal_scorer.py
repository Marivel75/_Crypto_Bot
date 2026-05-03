"""Scoring composite des signaux techniques : RSI, MACD, Bollinger Bands, SMA.

Retourne un signal ("buy" | "sell" | "hold"), un score [-1, +1] et les règles déclenchées.
"""

from __future__ import annotations


def score_candle(
    close: float | None,
    rsi: float | None,
    macd_line: float | None,
    macd_signal_val: float | None,
    bb_upper: float | None,
    bb_lower: float | None,
    sma_20: float | None,
    sma_50: float | None,
    macd_cross_up: bool = False,
    macd_cross_down: bool = False,
) -> tuple[str, float, list[str]]:
    """Score une bougie à partir de ses indicateurs.

    Returns:
        (signal, score, reasons)
        - signal : "buy" | "sell" | "hold"
        - score  : float [-1.0, +1.0]
        - reasons: règles déclenchées
    """
    votes: list[float] = []
    reasons: list[str] = []

    # ── RSI ──────────────────────────────────────────────────────
    if rsi is not None:
        if rsi < 30:
            votes.append(1.0)
            reasons.append(f"RSI survendu ({rsi:.1f})")
        elif rsi < 45:
            votes.append(0.5)
            reasons.append(f"RSI faiblement haussier ({rsi:.1f})")
        elif rsi > 70:
            votes.append(-1.0)
            reasons.append(f"RSI surachat ({rsi:.1f})")
        elif rsi > 55:
            votes.append(-0.5)
            reasons.append(f"RSI faiblement baissier ({rsi:.1f})")

    # ── MACD ─────────────────────────────────────────────────────
    if macd_cross_up:
        votes.append(1.0)
        reasons.append("Croisement MACD haussier")
    elif macd_cross_down:
        votes.append(-1.0)
        reasons.append("Croisement MACD baissier")
    elif macd_line is not None and macd_signal_val is not None:
        if macd_line > macd_signal_val:
            votes.append(0.3)
            reasons.append("MACD au-dessus du signal")
        else:
            votes.append(-0.3)
            reasons.append("MACD en dessous du signal")

    # ── Bollinger Bands ──────────────────────────────────────────
    if close is not None and bb_lower is not None and bb_upper is not None:
        if close < bb_lower:
            votes.append(1.0)
            reasons.append("Prix sous la bande BB inférieure")
        elif close > bb_upper:
            votes.append(-1.0)
            reasons.append("Prix au-dessus de la bande BB supérieure")

    # ── Tendance SMA ─────────────────────────────────────────────
    if close is not None and sma_20 is not None and sma_50 is not None:
        if close > sma_20 > sma_50:
            votes.append(0.5)
            reasons.append("Tendance haussière (prix > SMA20 > SMA50)")
        elif close < sma_20 < sma_50:
            votes.append(-0.5)
            reasons.append("Tendance baissière (prix < SMA20 < SMA50)")

    if not votes:
        return "hold", 0.0, []

    score = sum(votes) / len(votes)
    score = max(-1.0, min(1.0, score))

    if score > 0.3:
        signal = "buy"
    elif score < -0.3:
        signal = "sell"
    else:
        signal = "hold"

    return signal, round(score, 3), reasons
