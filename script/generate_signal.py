"""Generate trading signals for the dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

import requests

from .config import PortfolioConfig, ScoringWeights
from .data_fetch import fetch_ohlcv, load_portfolio_ids
from .indicators import IndicatorPayload, compute_indicators
from .scoring import ScoreResult, score_and_decision
from .validation import validate_ohlcv

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
PUBLIC_DIR.mkdir(exist_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ids",
        nargs="*",
        help="Override the asset IDs to process. Defaults to portfolio file or built-ins.",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        help="Number of days to fetch for each asset (default: config value).",
    )
    parser.add_argument(
        "--vs-currency",
        default=None,
        help="Reporting currency (default: config value).",
    )
    parser.add_argument(
        "--output",
        default=str(PUBLIC_DIR / "signals_by_asset.json"),
        help="Where to write the resulting JSON payload.",
    )
    return parser


def collect_portfolio_ids(args_ids, config: PortfolioConfig) -> list[str]:
    if args_ids:
        return list(dict.fromkeys(i.strip() for i in args_ids if i.strip()))
    return load_portfolio_ids(ROOT / config.portfolio_file, config.default_ids)


def summarise_indicator(ind: IndicatorPayload) -> Dict:
    return {
        "rsi14": round(ind.rsi14, 2) if ind.rsi14 is not None else None,
        "sma50": round(ind.sma50, 2) if ind.sma50 is not None else None,
        "sma50_slope": round(ind.sma50_slope, 2) if ind.sma50_slope is not None else None,
        "macd": {
            "macd": round(ind.macd.get("macd"), 4) if ind.macd.get("macd") is not None else None,
            "signal": round(ind.macd.get("signal"), 4) if ind.macd.get("signal") is not None else None,
            "hist": round(ind.macd.get("hist"), 6) if ind.macd.get("hist") is not None else None,
            "cross": ind.macd.get("cross"),
        },
        "bb_pctb": round(ind.bb_pctb, 4) if ind.bb_pctb is not None else None,
        "bb_width": round(ind.bb_width, 4) if ind.bb_width is not None else None,
        "atr_pct": round(ind.atr_pct, 2) if ind.atr_pct is not None else None,
    }


def generate_signals(config: PortfolioConfig, weights: ScoringWeights, args) -> Dict:
    ids = collect_portfolio_ids(args.ids, config)
    lookback = args.lookback or config.lookback_days
    vs_currency = args.vs_currency or config.vs_currency
    outfile = Path(args.output)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback)

    now_iso = datetime.now(timezone.utc).isoformat()
    results: Dict[str, Dict] = {}

    session = requests.Session()

    for cid in ids:
        try:
            df = fetch_ohlcv(cid, start, end, session=session)
        except Exception as exc:  # noqa: BLE001 - surfaced to payload as error.
            results[cid] = {"error": str(exc)}
            print(f"[WARN] {cid}: {exc}")
            continue

        issues = validate_ohlcv(df)
        if issues:
            msg = "; ".join(issues)
            results[cid] = {"error": msg}
            print(f"[SKIP] {cid} -> {msg}")
            continue

        ind = compute_indicators(df)

        required = [ind.rsi14, ind.sma50, ind.bb_pctb, ind.last_close, ind.macd.get("hist")]
        if any(val is None for val in required):
            msg = "indicateurs incomplets"
            results[cid] = {"error": msg}
            print(f"[SKIP] {cid} -> {msg}")
            continue

        score_result = score_and_decision(ind, weights)
        if score_result.score is None:
            msg = "score indisponible"
            results[cid] = {"error": msg}
            print(f"[SKIP] {cid} -> {msg}")
            continue

        results[cid] = build_asset_payload(cid, ind, score_result)
        print(f"[OK] {cid}")

    payload = {
        "meta": {
            "generated_at_utc": now_iso,
            "vs_currency": vs_currency,
            "lookback_days": lookback,
            "asset_count": len(ids),
        },
        "signals": results,
    }

    outfile.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {outfile} ({len(results)} assets).")
    return payload


def build_asset_payload(cid: str, ind: IndicatorPayload, score_result: ScoreResult) -> Dict:
    return {
        "symbol": cid.split("-")[0].upper(),
        "date": ind.last_time,
        "close": round(ind.last_close, 2) if ind.last_close is not None else None,
        "indicators": summarise_indicator(ind),
        "parts": score_result.parts,
        "score": score_result.score,
        "decision": score_result.decision,
        "percent": score_result.percent,
    }


def main(argv: list[str] | None = None) -> Dict:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = PortfolioConfig()
    weights = ScoringWeights()

    return generate_signals(config, weights, args)


if __name__ == "__main__":
    main()

