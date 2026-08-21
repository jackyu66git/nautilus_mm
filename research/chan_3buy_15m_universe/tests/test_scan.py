import unittest

from chan_3buy_15m_universe.scan import scan_third_tf


class UniverseTfTest(unittest.TestCase):
    def test_empty_bars_have_no_events(self):
        import pandas as pd

        idx = pd.date_range("2026-01-01", periods=5, freq="15min", tz="UTC")
        bar = pd.DataFrame(
            {
                "open_ts": idx,
                "close_ts": idx + pd.Timedelta(minutes=15),
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1.0,
            }
        )
        out = scan_third_tf(bar, "15m")
        self.assertEqual(out["n_3"], 0)
        self.assertEqual(out["timeframe"], "15m")


if __name__ == "__main__":
    unittest.main()
