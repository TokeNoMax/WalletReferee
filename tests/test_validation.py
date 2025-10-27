import unittest

import pandas as pd

from script.validation import validate_ohlcv


class ValidationTests(unittest.TestCase):
    def test_detects_missing_columns(self):
        df = pd.DataFrame({"time": pd.date_range("2023-01-01", periods=5, tz="UTC")})
        issues = validate_ohlcv(df)
        self.assertIn("missing columns", issues[0])

    def test_detects_duplicate_timestamps(self):
        times = pd.to_datetime(
            ["2023-01-01", "2023-01-02", "2023-01-02", "2023-01-03"], utc=True
        )
        df = pd.DataFrame(
            {
                "time": times,
                "open": [1, 2, 3, 4],
                "high": [2, 3, 4, 5],
                "low": [0.5, 1.5, 2.5, 3.5],
                "close": [1.5, 2.5, 3.5, 4.5],
                "volume": [10, 11, 12, 13],
            }
        )
        issues = validate_ohlcv(df)
        self.assertIn("duplicate timestamps", issues)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
