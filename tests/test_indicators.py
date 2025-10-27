import unittest

import numpy as np
import pandas as pd

from script.indicators import IndicatorPayload, compute_indicators


class ComputeIndicatorsTests(unittest.TestCase):
    def setUp(self):
        periods = 80
        base = 100
        trend = np.linspace(0, 20, periods)
        close = base + trend
        high = close + 2
        low = close - 2
        open_ = close - 1
        volume = np.linspace(1_000, 2_000, periods)
        time_index = pd.date_range(
            "2023-01-01", periods=periods, freq="D", tz="UTC"
        )

        self.df = pd.DataFrame(
            {
                "time": time_index,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    def test_compute_indicators_returns_complete_payload(self):
        payload = compute_indicators(self.df)
        self.assertIsInstance(payload, IndicatorPayload)

        self.assertIsNotNone(payload.rsi14)
        self.assertIsNotNone(payload.sma50)
        self.assertIsNotNone(payload.sma50_slope)
        self.assertIsNotNone(payload.bb_pctb)
        self.assertIsNotNone(payload.bb_width)
        self.assertIsNotNone(payload.macd["hist"])
        self.assertIn(payload.macd["cross"], {"bull", "bear", "none"})
        self.assertIsNotNone(payload.atr_pct)
        self.assertEqual(payload.last_time, self.df["time"].iloc[-1].isoformat())
        self.assertGreater(payload.last_close, 0)


if __name__ == "__main__":  # pragma: no cover - allows `python tests/test_indicators.py`
    unittest.main()
