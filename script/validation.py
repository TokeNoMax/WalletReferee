"""Validation utilities for the OHLCV datasets."""

from __future__ import annotations

from typing import List

import pandas as pd


class ValidationError(Exception):
    """Raised when the input dataset does not meet basic requirements."""


def validate_ohlcv(df: pd.DataFrame) -> List[str]:
    """Return a list of validation issues detected for the dataframe."""

    issues: List[str] = []

    required_columns = {"time", "open", "high", "low", "close", "volume"}
    missing = required_columns.difference(df.columns)
    if missing:
        issues.append(f"missing columns: {sorted(missing)}")
        return issues

    if df.empty:
        issues.append("empty dataset")
        return issues

    if not df["time"].is_monotonic_increasing:
        issues.append("timestamps not sorted")

    if df["time"].duplicated().any():
        issues.append("duplicate timestamps")

    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        if df[col].isna().all():
            issues.append(f"column {col} entirely missing")
        elif df[col].dtype == object and not pd.to_numeric(df[col], errors="coerce").notna().all():
            issues.append(f"column {col} contains non-numeric values")

    return issues

