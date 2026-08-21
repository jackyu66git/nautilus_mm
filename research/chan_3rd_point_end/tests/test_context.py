import unittest

import pandas as pd

from chan_3rd_point_end.context import htf_at, segment


class EndCtxTest(unittest.TestCase):
    def test_segment_frozen_cuts(self):
        self.assertEqual(segment("TREND_UP", 6), "EARLY")
        self.assertEqual(segment("TREND_UP", 24), "MID")
        self.assertEqual(segment("TREND_DOWN", 48), "LATE")
        self.assertEqual(segment("RANGE", 100), "SHIFT")

    def test_htf_at_uses_only_closed_bars(self):
        snaps = [
            {"close_ts": pd.Timestamp("2026-01-01 02:00:00+00:00")},
            {"close_ts": pd.Timestamp("2026-01-01 03:00:00+00:00")},
        ]
        hit = htf_at(snaps, pd.Timestamp("2026-01-01 02:30:00+00:00"))
        self.assertEqual(hit["close_ts"], snaps[0]["close_ts"])


if __name__ == "__main__":
    unittest.main()
