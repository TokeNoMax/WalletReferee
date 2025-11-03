#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère public/signal.json à partir de prix CoinGecko.
Robuste (degraded mode), explicable (reason, confidence), traçable (generatedAt, version).
"""
import os, sys, json, time, math, datetime as dt
from typing import List, Dict, Any
import requests
import pandas as pd
import numpy as np

# ===== Configuration =====
# Edite ta liste ici (id CoinGecko + symbole d’affichage)
PORTFOLIO = [
    {"id": "bitcoin", "symbol": "BTC"},
    {"id": "ethereum", "symbol": "ETH"},
    {"id": "solana", "symbol": "SOL"},
]
VS_CCY = "usd"
DAYS = 120  # historique pour MA/RSI
OUTPUT = "public/signal.json"
VERSION = "1"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "WalletReferee/1.0 (+github actions)"})


def now_iso():
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def fetch_market_chart(coin_id: str, vs: str = VS_CCY, days: int = DAYS) -> pd.DataFrame:
    """CoinGecko market_chart: close-only (daily-ish)."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs, "days": days, "interval": "daily"}
    r = SESSION.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    prices = data.get("prices", [])
    if not prices:
        raise RuntimeError(f"No prices for {coin_id}")
    # prices: [ [ms, price], ... ]
    df = pd.DataFrame(prices, columns=["ts_ms", "close"])
    df["date"] = pd.to_datetime(df["ts_ms"], unit="ms")
    df = df[["date", "close"]].dropna()
    df = df.sort_values("date").reset_index(drop=True)
    return df


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up).ewm(alpha=1/period, adjust=False).mean()
    roll_down = pd.Series(down).ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-12)
    rsi_val = 100.0 - (100.0 / (1.0 + rs))
    return pd.Series(rsi_val, index=series.index)


def decide_signal(price: float, sma20: float, sma50: float, rsi14: float,
                  slope20: float) -> (str, float, str):
    """Règles simples + confidence."""
    votes = []
    reasons = []

    # Trend/MAs
    if price > sma20 > sma50:
        votes.append(1); reasons.append("Trend up: price>SMA20>SMA50")
    elif price < sma20 < sma50:
        votes.append(-1); reasons.append("Trend down: price<SMA20<SMA50")

    # RSI zones
    if rsi14 < 30:
        votes.append(1); reasons.append("RSI<30 (oversold)")
    elif rsi14 > 70:
        votes.append(-1); reasons.append("RSI>70 (overbought)")
    else:
        votes.append(0); reasons.append("RSI neutral")

    # Slope SMA20
    if slope20 > 0:
        votes.append(1); reasons.append("SMA20 slope up")
    elif slope20 < 0:
        votes.append(-1); reasons.append("SMA20 slope down")

    score = sum(votes)
    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Confidence: normalise par nb de règles
    confidence = min(1.0, max(0.0, (abs(score) / 3.0)))
    reason = "; ".join(reasons)
    return signal, float(confidence), reason


def build_entry(coin: Dict[str, str]) -> Dict[str, Any]:
    cid = coin["id"]; symbol = coin["symbol"]
    df = fetch_market_chart(cid, VS_CCY, DAYS)
    close = df["close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    rsi14 = rsi(close, 14)

    # pente SMA20 ~ diff des 3 derniers points
    slope20 = (sma20.iloc[-1] - sma20.iloc[-3]) if len(sma20) >= 3 else 0.0

    last = {
        "price": float(close.iloc[-1]),
        "sma20": float(sma20.iloc[-1]),
        "sma50": float(sma50.iloc[-1]),
        "rsi14": float(rsi14.iloc[-1]),
        "slope20": float(slope20),
    }
    signal, confidence, reason = decide_signal(
        last["price"], last["sma20"], last["sma50"], last["rsi14"], last["slope20"]
    )
    return {
        "id": cid,
        "symbol": symbol,
        "signal": signal,
        "confidence": round(confidence, 3),
        "price": round(last["price"], 6),
        "reason": reason,
        "timestamp": now_iso(),
    }


def main():
    errors = []
    entries = []
    for coin in PORTFOLIO:
        try:
            entries.append(build_entry(coin))
        except Exception as e:
            errors.append(f'{coin["id"]}: {e}')

    status = "ok" if not errors and entries else "degraded"
    out = {
        "version": VERSION,
        "generatedAt": now_iso(),
        "status": status,
        "entries": entries,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Logs lisibles dans les artefacts Actions
    print("=== WalletReferee generation ===")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if errors:
        print("Errors:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        # Code 0 pour ne pas casser le run si on a au moins un entry
        if not entries:
            sys.exit(1)


if __name__ == "__main__":
    main()
