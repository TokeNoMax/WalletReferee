"""Scoring and decision logic for generated signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .config import ScoringWeights
from .indicators import IndicatorPayload


@dataclass
class ScoreResult:
    score: float | None
    decision: str
    percent: int | None
    parts: Dict[str, float]


def score_and_decision(ind: IndicatorPayload, weights: ScoringWeights) -> ScoreResult:
    rsi = ind.rsi14
    pctb = ind.bb_pctb
    macd_hist = ind.macd.get("hist") if ind.macd else None
    atr_pct = ind.atr_pct
    slope = ind.sma50_slope

    if any(v is None for v in (rsi, pctb, macd_hist)):
        return ScoreResult(score=None, decision="HOLD", percent=None, parts={})

    score = weights.base
    parts = {"base": weights.base * 100}

    if rsi < 30:
        score += weights.rsi_bonus
        parts["rsi"] = weights.rsi_bonus * 100
    elif rsi > 70:
        score -= weights.rsi_penalty
        parts["rsi"] = -weights.rsi_penalty * 100
    else:
        parts["rsi"] = 0

    if pctb < 0.2:
        score += weights.bollinger_bonus
        parts["bollinger"] = weights.bollinger_bonus * 100
    elif pctb > 0.8:
        score -= weights.bollinger_penalty
        parts["bollinger"] = -weights.bollinger_penalty * 100
    else:
        parts["bollinger"] = 0

    if macd_hist and macd_hist > 0:
        score += weights.macd_bonus
        parts["macd"] = weights.macd_bonus * 100
    else:
        score -= weights.macd_penalty
        parts["macd"] = -weights.macd_penalty * 100

    if slope is not None:
        slope_adj = max(
            -weights.max_slope_adjustment,
            min(weights.max_slope_adjustment, slope / 10.0),
        )
        score += slope_adj
        parts["sma50_slope"] = round(slope_adj * 100, 1)

    if atr_pct is not None:
        if atr_pct > weights.high_volatility_threshold:
            score -= weights.volatility_adjustment
            parts["atr"] = -weights.volatility_adjustment * 100
        elif atr_pct < weights.low_volatility_threshold:
            score += weights.volatility_adjustment
            parts["atr"] = weights.volatility_adjustment * 100
        else:
            parts["atr"] = 0

    score = max(0.0, min(1.0, score))
    percent = int(round(score * 100))
    parts["total"] = percent

    decision = "BUY" if score >= 0.65 else "SELL" if score <= 0.35 else "HOLD"
    return ScoreResult(score=round(score, 2), decision=decision, percent=percent, parts=parts)

