import unittest

from script.config import ScoringWeights
from script.indicators import IndicatorPayload
from script.scoring import score_and_decision


class ScoringTests(unittest.TestCase):
    def test_bullish_payload_returns_buy(self):
        payload = IndicatorPayload(
            rsi14=25.0,
            sma50=100.0,
            sma50_slope=8.0,
            bb_pctb=0.1,
            bb_width=0.3,
            macd={"macd": 0.5, "signal": 0.2, "hist": 0.3, "cross": "bull"},
            atr_pct=3.0,
            last_close=150.0,
            last_time="2023-03-01T00:00:00+00:00",
        )
        result = score_and_decision(payload, ScoringWeights())
        self.assertEqual(result.decision, "BUY")
        self.assertGreaterEqual(result.score, 0.65)
        self.assertIn("total", result.parts)

    def test_bearish_payload_returns_sell(self):
        payload = IndicatorPayload(
            rsi14=80.0,
            sma50=90.0,
            sma50_slope=-6.0,
            bb_pctb=0.9,
            bb_width=0.3,
            macd={"macd": -0.2, "signal": 0.1, "hist": -0.3, "cross": "bear"},
            atr_pct=20.0,
            last_close=80.0,
            last_time="2023-03-01T00:00:00+00:00",
        )
        result = score_and_decision(payload, ScoringWeights())
        self.assertEqual(result.decision, "SELL")
        self.assertLessEqual(result.score, 0.35)
        self.assertIn("atr", result.parts)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
