"""Pure indicator implementations used by the signal generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


def safe_num(value):
    try:
        numeric = float(value)
    except Exception:  # noqa: BLE001 - safe conversion helper.
        return None

    if np.isnan(numeric) or np.isinf(numeric):
        return None
    return numeric


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def compute_bollinger(series: pd.Series, window: int = 20, dev: int = 2) -> Dict[str, pd.Series]:
    mid = compute_sma(series, window)
    std = series.rolling(window=window, min_periods=window).std(ddof=0)
    upper = mid + dev * std
    lower = mid - dev * std
    band = upper - lower
    pctb = ((series - lower) / band).where(band != 0)
    width = (band / mid).where(mid != 0)
    return {"pctb": pctb, "width": width}


def compute_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, pd.Series]:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "hist": hist}


def compute_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


@dataclass
class IndicatorPayload:
    rsi14: float | None
    sma50: float | None
    sma50_slope: float | None
    bb_pctb: float | None
    bb_width: float | None
    macd: Dict[str, float | str | None]
    atr_pct: float | None
    last_close: float | None
    last_time: str | None


def compute_indicators(df: pd.DataFrame) -> IndicatorPayload:
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    rsi = compute_rsi(close)
    sma50 = compute_sma(close, window=50)
    bb = compute_bollinger(close, window=20, dev=2)
    macd = compute_macd(close)
    atr = compute_atr(high, low, close, window=14)

    macd_hist_series = macd["hist"]
    macd_line_series = macd["macd"]
    macd_signal_series = macd["signal"]

    sma50_series = sma50.dropna()
    slope = None
    if len(sma50_series) >= 5:
        last_val = safe_num(sma50_series.iloc[-1])
        prev_val = safe_num(sma50_series.iloc[-5])
        if prev_val not in (None, 0.0) and last_val is not None:
            slope = safe_num(((last_val - prev_val) / prev_val) * 100)

    macd_cross = "none"
    macd_hist_vals = macd_hist_series.dropna()
    if len(macd_hist_vals) >= 2:
        prev_hist = macd_hist_vals.iloc[-2]
        last_hist = macd_hist_vals.iloc[-1]
        if prev_hist <= 0 < last_hist:
            macd_cross = "bull"
        elif prev_hist >= 0 > last_hist:
            macd_cross = "bear"

    atr_series = atr
    atr_pct = None
    if len(close):
        last_close = safe_num(close.iloc[-1])
        atr_values = atr_series.dropna()
        last_atr = safe_num(atr_values.iloc[-1]) if len(atr_values) else None
        if last_close not in (None, 0.0) and last_atr is not None:
            atr_pct = safe_num((last_atr / last_close) * 100)

    return IndicatorPayload(
        rsi14=safe_num(rsi.iloc[-1]),
        sma50=safe_num(sma50.iloc[-1]),
        sma50_slope=slope,
        bb_pctb=safe_num(bb["pctb"].iloc[-1]),
        bb_width=safe_num(bb["width"].iloc[-1]),
        macd={
            "macd": safe_num(macd_line_series.iloc[-1]),
            "signal": safe_num(macd_signal_series.iloc[-1]),
            "hist": safe_num(macd_hist_series.iloc[-1]),
            "cross": macd_cross,
        },
        atr_pct=atr_pct,
        last_close=safe_num(close.iloc[-1]) if len(close) else None,
        last_time=df["time"].iloc[-1].isoformat() if len(df) else None,
    )

