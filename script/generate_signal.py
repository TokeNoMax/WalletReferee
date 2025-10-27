# script/generate_signal.py
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

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

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def compute_bollinger(series: pd.Series, window: int = 20, dev: int = 2) -> dict:
    mid = compute_sma(series, window)
    std = series.rolling(window=window, min_periods=window).std(ddof=0)
    upper = mid + dev * std
    lower = mid - dev * std
    band = upper - lower
    pctb = ((series - lower) / band).where(band != 0)
    width = (band / mid).where(mid != 0)
    return {"pctb": pctb, "width": width}


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "hist": hist}


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
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


def compute_indicators(df: pd.DataFrame) -> dict:
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

    out = {
        "rsi14": safe_num(rsi.iloc[-1]),
        "sma50": safe_num(sma50.iloc[-1]),
        "sma50_slope": slope,
        "bb_pctb": safe_num(bb["pctb"].iloc[-1]),
        "bb_width": safe_num(bb["width"].iloc[-1]),
        "macd": {
            "macd": safe_num(macd_line_series.iloc[-1]),
            "signal": safe_num(macd_signal_series.iloc[-1]),
            "hist": safe_num(macd_hist_series.iloc[-1]),
            "cross": macd_cross,
        },
        "atr_pct": atr_pct,
        "last_close": safe_num(close.iloc[-1]) if len(close) else None,
        "last_time": df["time"].iloc[-1].isoformat() if len(df) else None,
    }
    return out


def score_and_decision(ind: dict) -> dict:
    rsi = ind.get("rsi14")
    pctb = ind.get("bb_pctb")
    macd_hist = ind.get("macd", {}).get("hist")
    atr_pct = ind.get("atr_pct")
    slope = ind.get("sma50_slope")

    if any(v is None for v in (rsi, pctb, macd_hist)):
        return {"score": None, "decision": "HOLD", "parts": {}}

    score = 0.5
    parts = {"base": 50}

    if rsi < 30:
        score += 0.2
        parts["rsi"] = 20
    elif rsi > 70:
        score -= 0.2
        parts["rsi"] = -20
    else:
        parts["rsi"] = 0

    if pctb < 0.2:
        score += 0.15
        parts["bollinger"] = 15
    elif pctb > 0.8:
        score -= 0.15
        parts["bollinger"] = -15
    else:
        parts["bollinger"] = 0

    if macd_hist > 0:
        score += 0.1
        parts["macd"] = 10
    else:
        score -= 0.1
        parts["macd"] = -10

    if slope is not None:
        slope_adj = max(-0.05, min(0.05, slope / 10.0))
        score += slope_adj
        parts["sma50_slope"] = round(slope_adj * 100, 1)

    if atr_pct is not None:
        vol_adj = -0.05 if atr_pct > 10 else 0.05 if atr_pct < 5 else 0.0
        score += vol_adj
        parts["atr"] = round(vol_adj * 100, 1)

    score = max(0.0, min(1.0, score))
    percent = int(round(score * 100))
    parts["total"] = percent

    decision = "BUY" if score >= 0.65 else "SELL" if score <= 0.35 else "HOLD"
    return {"score": round(score, 2), "decision": decision, "percent": percent, "parts": parts}

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

    now_iso = datetime.now(timezone.utc).isoformat()
    results = {}
    for cid in ids:
        try:
            df = fetch_ohlcv(cid, start, end)
            ind = compute_indicators(df)

            # Tous les indicateurs principaux doivent être numériques
            if any(
                ind.get(key) is None
                for key in ("rsi14", "sma50", "bb_pctb", "last_close")
            ) or ind.get("macd", {}).get("hist") is None:
                print(f"[SKIP] {cid} -> indicateurs incomplets")
                results[cid] = {"error": "indicateurs incomplets"}
                continue

            rec = score_and_decision(ind)

            if rec["score"] is None:
                results[cid] = {"error": "score indisponible"}
                print(f"[SKIP] {cid} -> score indisponible")
                continue

            results[cid] = {
                "symbol": cid.split("-")[0].upper(),
                "date": ind["last_time"],
                "close": round(ind["last_close"], 2) if ind["last_close"] is not None else None,
                "indicators": {
                    "rsi14": round(ind["rsi14"], 2) if ind["rsi14"] is not None else None,
                    "sma50": round(ind["sma50"], 2) if ind["sma50"] is not None else None,
                    "sma50_slope": round(ind["sma50_slope"], 2) if ind["sma50_slope"] is not None else None,
                    "macd": {
                        "macd": round(ind["macd"]["macd"], 4) if ind["macd"]["macd"] is not None else None,
                        "signal": round(ind["macd"]["signal"], 4) if ind["macd"]["signal"] is not None else None,
                        "hist": round(ind["macd"]["hist"], 6) if ind["macd"]["hist"] is not None else None,
                        "cross": ind["macd"]["cross"],
                    },
                    "bb_pctb": round(ind["bb_pctb"], 4) if ind["bb_pctb"] is not None else None,
                    "bb_width": round(ind["bb_width"], 4) if ind["bb_width"] is not None else None,
                    "atr_pct": round(ind["atr_pct"], 2) if ind["atr_pct"] is not None else None,
                },
                "parts": rec["parts"],
                "score": rec["score"],
                "decision": rec["decision"],
                "percent": rec["percent"],
            }
            print(f"[OK] {cid}")
        except Exception as e:
            print(f"[WARN] {cid}: {e}")
            results[cid] = {"error": str(e)}

    payload = {
        "meta": {
            "generated_at_utc": now_iso,
            "vs_currency": "usd",
        },
        "signals": results,
    }

    OUTFILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUTFILE} ({len(results)} assets).")

if __name__ == "__main__":
    main()
