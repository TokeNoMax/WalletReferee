# script/generate_signal.py
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from ta.volatility import BollingerBands

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
PUBLIC_DIR.mkdir(exist_ok=True)

PORTFOLIO_FILE = PUBLIC_DIR / "portfolio_ids.json"
OUTFILE = PUBLIC_DIR / "signals_by_asset.json"

DEFAULT_IDS = ["btc-bitcoin", "eth-ethereum", "solana-solana"]
DAYS = 200

def fetch_ohlcv(coin_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    url = (
        f"https://api.coinpaprika.com/v1/tickers/{coin_id}/ohlcv/historical"
        f"?start={start.strftime('%Y-%m-%d')}&end={end.strftime('%Y-%m-%d')}"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"Empty OHLCV for {coin_id}")
    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)

def safe_num(x):
    try:
        f = float(x)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except Exception:
        return None

def compute_indicators(df: pd.DataFrame) -> dict:
    close = df["close"].astype(float)
    rsi = RSIIndicator(close).rsi()
    sma50 = SMAIndicator(close, window=50).sma_indicator()
    bb = BollingerBands(close, window=20, window_dev=2).bollinger_pband()
    macd_hist = MACD(close, window_slow=26, window_fast=12, window_sign=9).macd_diff()

    out = {
        "rsi14": safe_num(rsi.iloc[-1]),
        "sma50": safe_num(sma50.iloc[-1]),
        "bb_pctb": safe_num(bb.iloc[-1]),
        "macd_hist": safe_num(macd_hist.iloc[-1]),
        "last_close": safe_num(close.iloc[-1]) if len(close) else None,
        "last_time": df["time"].iloc[-1].isoformat() if len(df) else None,
    }
    return out

def score_and_decision(ind: dict) -> dict:
    rsi = ind.get("rsi14")
    pctb = ind.get("bb_pctb")
    macd = ind.get("macd_hist")
    if rsi is None or pctb is None or macd is None:
        return {"score": None, "decision": "HOLD"}

    score = 0.5
    if rsi < 30: score += 0.2
    elif rsi > 70: score -= 0.2

    if pctb < 0.2: score += 0.15
    elif pctb > 0.8: score -= 0.15

    if macd > 0: score += 0.1
    else: score -= 0.1

    score = max(0.0, min(1.0, score))
    return {"score": round(score, 2), "decision": "BUY" if score >= 0.65 else "SELL" if score <= 0.35 else "HOLD"}

def main():
    if PORTFOLIO_FILE.exists():
        try:
            ids = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
            if not isinstance(ids, list) or not ids:
                ids = DEFAULT_IDS
        except Exception:
            ids = DEFAULT_IDS
    else:
        ids = DEFAULT_IDS

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)

    results = {}
    for cid in ids:
        try:
            df = fetch_ohlcv(cid, start, end)
            ind = compute_indicators(df)

            # Tous les indicateurs doivent être numériques
            if any(ind[k] is None for k in ("rsi14", "sma50", "bb_pctb", "macd_hist", "last_close")):
                print(f"[SKIP] {cid} -> indicateurs incomplets")
                continue

            rec = score_and_decision(ind)

            results[cid] = {
                "id": cid,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "indicators": {
                    "rsi14": round(ind["rsi14"], 2),
                    "sma50": round(ind["sma50"], 2),
                    "bb_pctb": round(ind["bb_pctb"], 4),
                    "macd_hist": round(ind["macd_hist"], 6)
                },
                "close": round(ind["last_close"], 2),
                "last_time": ind["last_time"],
                "score": rec["score"],
                "decision": rec["decision"],
            }
            print(f"[OK] {cid}")
        except Exception as e:
            print(f"[WARN] {cid}: {e}")

    OUTFILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUTFILE} ({len(results)} assets).")

if __name__ == "__main__":
    main()
