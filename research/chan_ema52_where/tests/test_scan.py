import unittest

import pandas as pd

from chan_ema52_where.scan import add_indicators, scan_episodes


def _bars(n: int, close) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    c = pd.Series(close, dtype=float)
    return pd.DataFrame(
        {
            "open_ts": idx,
            "close_ts": idx + pd.Timedelta(hours=1),
            "open": c,
            "high": c + 10,
            "low": c - 10,
            "close": c,
            "volume": 1.0,
        }
    )


class EmaWhereTest(unittest.TestCase):
    def test_ema_is_causal_ewm(self):
        bar = _bars(80, list(range(80)))
        d = add_indicators(bar)
        self.assertEqual(len(d["ema"].dropna()), 80)
        self.assertGreater(d["ema"].iloc[-1], d["ema"].iloc[40])

    def test_near_clock_before_end(self):
        # rising then a dip toward a lagging ema, then new high
        px = [100 + i * 2 for i in range(70)]
        px += [px[-1] - 8, px[-1] - 20, px[-1] - 35, px[-1] - 15, px[-1] + 10]
        bar = _bars(len(px), px)
        eps = scan_episodes(bar)
        for e in eps:
            if e["near"] and e["T_NEAR_VISIBLE"]:
                self.assertLess(e["T_SWING_VISIBLE"], e["T_NEAR_VISIBLE"])
                self.assertLessEqual(e["T_NEAR_VISIBLE"], e["T_END"])


if __name__ == "__main__":
    unittest.main()
