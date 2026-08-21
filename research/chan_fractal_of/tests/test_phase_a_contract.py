import unittest

from chan_fractal_of.frozen_config import assert_phase_a_clean
from chan_fractal_of.of_window import _clip
import pandas as pd


class PhaseAContractTest(unittest.TestCase):
    def test_b1_pollution(self):
        with self.assertRaises(ValueError):
            assert_phase_a_clean({"fx_id": "x", "B1": 1})
        assert_phase_a_clean({"fx_id": "x", "of_delta_forming": 0.1})

    def test_clip_excludes_visible_and_after(self):
        of = pd.DataFrame(
            {
                "open_ts": pd.to_datetime(
                    ["2026-06-20 10:00", "2026-06-20 10:14", "2026-06-20 10:15", "2026-06-20 10:16"],
                    utc=True,
                )
            }
        )
        vis = pd.Timestamp("2026-06-20 10:15", tz="UTC")
        start = pd.Timestamp("2026-06-20 10:00", tz="UTC")
        end = pd.Timestamp("2026-06-20 10:30", tz="UTC")
        w = _clip(of, start, end, vis)
        self.assertTrue((w["open_ts"] < vis).all())
        self.assertEqual(len(w), 2)


if __name__ == "__main__":
    unittest.main()
