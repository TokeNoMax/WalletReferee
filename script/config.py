"""Configuration objects for the signal generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class PortfolioConfig:
    """Configuration describing the portfolio universe and lookback."""

    default_ids: List[str] = field(
        default_factory=lambda: [
            "btc-bitcoin",
            "eth-ethereum",
            "solana-solana",
        ]
    )
    lookback_days: int = 200
    vs_currency: str = "usd"
    portfolio_file: Path = Path("public/portfolio_ids.json")


@dataclass(frozen=True)
class ScoringWeights:
    """Tunable coefficients for the scoring algorithm."""

    base: float = 0.5
    rsi_bonus: float = 0.2
    rsi_penalty: float = 0.2
    bollinger_bonus: float = 0.15
    bollinger_penalty: float = 0.15
    macd_bonus: float = 0.1
    macd_penalty: float = 0.1
    max_slope_adjustment: float = 0.05
    low_volatility_threshold: float = 5.0
    high_volatility_threshold: float = 10.0
    volatility_adjustment: float = 0.05

