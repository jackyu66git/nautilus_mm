import unittest

from chan_3rd_point_fate.scan import follow_fate
import pandas as pd


def _bar():
    idx = pd.date_range("2026-01-01", periods=6, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "open_ts": idx,
            "close_ts": idx + pd.Timedelta(minutes=15),
            "open": [100, 101, 102, 103, 90, 80],
            "high": [100, 101, 110, 103, 90, 80],
            "low": [100, 101, 102, 103, 90, 80],
            "close": [100, 101, 102, 103, 90, 80],
            "volume": 1.0,
        }
    )


class FateTest(unittest.TestCase):
    def test_b3_resume_before_reentry(self):
        ev = {
            "event_id": "x:B3:y",
            "kind": "B3",
            "tape_row": 0,
            "zg": 95.0,
            "zd": 85.0,
            "T_3_VISIBLE": "2026-01-01 00:15:00+00:00",
        }
        rec = follow_fate(ev, _bar())
        self.assertEqual(rec["fate"], "RESUME")


if __name__ == "__main__":
    unittest.main()
