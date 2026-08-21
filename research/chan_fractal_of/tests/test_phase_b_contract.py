import unittest

import numpy as np
import pandas as pd

from chan_fractal_of.audit_b import cliffs_delta
from chan_fractal_of.frozen_config import assert_phase_a_clean, assert_phase_b_features_clean
from chan_fractal_of.of_window import _clip


class PhaseBContractTest(unittest.TestCase):
    def test_labels_allowed_on_record_not_as_features(self):
        rec = {
            "fx_id": "x",
            "of_delta_forming": 0.1,
            "label_B1": 1,
            "label_B1_B2": 0,
            "label_bi_endpoint": 1,
            "mid_range": 12.0,
        }
        assert_phase_b_features_clean(rec)
        with self.assertRaises(ValueError):
            assert_phase_a_clean({"fx_id": "x", "B1": 1, "of_delta_forming": 0.1})

    def test_clip_still_excludes_visible(self):
        of = pd.DataFrame(
            {
                "open_ts": pd.to_datetime(
                    ["2026-06-20 10:00", "2026-06-20 10:14", "2026-06-20 10:15"],
                    utc=True,
                )
            }
        )
        vis = pd.Timestamp("2026-06-20 10:15", tz="UTC")
        w = _clip(of, pd.Timestamp("2026-06-20 10:00", tz="UTC"), pd.Timestamp("2026-06-20 10:30", tz="UTC"), vis)
        self.assertTrue((w["open_ts"] < vis).all())
        self.assertEqual(len(w), 2)

    def test_cliffs_delta_extremes(self):
        self.assertEqual(cliffs_delta(np.array([3, 4, 5]), np.array([0, 1, 2])), 1.0)
        self.assertEqual(cliffs_delta(np.array([1, 1, 1]), np.array([1, 1, 1])), 0.0)


if __name__ == "__main__":
    unittest.main()
