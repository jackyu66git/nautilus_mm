import unittest

import numpy as np
import pandas as pd

from chan_bi_of_strata.audit import _median_spearman
from chan_bi_of_strata.frozen_config import FEE_RT, assert_clean
from chan_bi_of_strata.path import path_stats
from chan_fractal_of.of_window import _clip


class StrataContractTest(unittest.TestCase):
    def test_no_b1(self):
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "B1": 1})
        assert_clean({"fx_id": "x", "of_delta_forming": 1.0, "mae_16": 0.01})

    def test_fee_frozen(self):
        self.assertEqual(FEE_RT, 0.0008)

    def test_median_spearman_monotone(self):
        self.assertAlmostEqual(_median_spearman([5, 4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(_median_spearman([1, 2, 3, 4, 5]), 1.0)
        self.assertTrue(abs(_median_spearman([1, 5, 2, 4, 3])) < 0.6)

    def test_of_clip(self):
        of = pd.DataFrame(
            {"open_ts": pd.to_datetime(["2026-06-20 10:00", "2026-06-20 10:15"], utc=True)}
        )
        vis = pd.Timestamp("2026-06-20 10:15", tz="UTC")
        w = _clip(of, vis - pd.Timedelta(minutes=15), vis + pd.Timedelta(minutes=15), vis)
        self.assertTrue((w["open_ts"] < vis).all())

    def test_long_path(self):
        idx = pd.date_range("2026-06-20", periods=20, freq="15min", tz="UTC")
        bar = pd.DataFrame(
            {
                "close_ts": idx + pd.Timedelta(minutes=15),
                "open": 100.0,
                "high": np.linspace(101, 110, 20),
                "low": np.linspace(99, 98, 20),
                "close": np.linspace(100, 108, 20),
            }
        )
        s = path_stats(bar, 0, "BOTTOM")
        self.assertIsNotNone(s)
        self.assertGreater(s["mfe_16"], 0)
        self.assertGreater(s["mae_16"], 0)
        self.assertAlmostEqual(s["ret_16_net"], s["ret_16"] - FEE_RT)


if __name__ == "__main__":
    unittest.main()
