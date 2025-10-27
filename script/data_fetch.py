"""HTTP retrieval helpers for the signal generator."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd
import requests


def load_portfolio_ids(path: Path, fallback: Sequence[str]) -> List[str]:
    """Return the list of portfolio IDs from disk, or the fallback."""

    if not path.exists():
        return list(fallback)

    try:
        ids = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return list(fallback)

    if not isinstance(ids, Iterable):
        return list(fallback)

    cleaned = [str(v).strip() for v in ids if str(v).strip()]
    return cleaned or list(fallback)


def fetch_ohlcv(
    coin_id: str,
    start: datetime,
    end: datetime,
    *,
    retries: int = 2,
    backoff_seconds: int = 2,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV data from CoinPaprika with basic retry logic."""

    url = (
        f"https://api.coinpaprika.com/v1/tickers/{coin_id}/ohlcv/historical"
        f"?start={start.strftime('%Y-%m-%d')}&end={end.strftime('%Y-%m-%d')}"
    )

    attempt = 0
    last_exc: Exception | None = None
    client = session or requests.Session()

    while attempt <= retries:
        try:
            response = client.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                raise ValueError(f"Empty OHLCV for {coin_id}")
            df = pd.DataFrame(payload)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            return df.sort_values("time").reset_index(drop=True)
        except Exception as exc:  # noqa: BLE001 - bubble up the last error.
            last_exc = exc
            if attempt == retries:
                break
            time.sleep(backoff_seconds * (attempt + 1))
        finally:
            attempt += 1

    assert last_exc is not None
    raise last_exc

