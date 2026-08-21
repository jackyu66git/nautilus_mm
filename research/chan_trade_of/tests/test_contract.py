import json
import unittest

import numpy as np
import pandas as pd

from chan_trade_of.frozen_config import assert_clean
from chan_trade_of.trades import clip_trades


class TradeOfContractTest(unittest.TestCase):
    def test_no_absorption_flag(self):
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "absorption_flag": 1})
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "B1": 1})
        assert_clean({"fx_id": "x", "hhi": 0.2, "speed": 1.0, "push": 0.01})

    def test_clip_excludes_visible(self):
        t = pd.DataFrame(
            {
                "ts": pd.to_datetime(
                    [
                        "2026-06-20 10:00:00",
                        "2026-06-20 10:14:59",
                        "2026-06-20 10:15:00",
                        "2026-06-20 10:16:00",
                    ],
                    utc=True,
                ),
                "price": [1, 1, 1, 1],
                "qty": [1, 1, 1, 1],
                "delta": [1, 1, 1, 1],
                "is_buyer_maker": [False, False, False, False],
            }
        )
        vis = pd.Timestamp("2026-06-20 10:15:00", tz="UTC")
        w = clip_trades(t, vis - pd.Timedelta(minutes=15), vis + pd.Timedelta(minutes=15), vis)
        self.assertTrue((w["ts"] < vis).all())
        self.assertEqual(len(w), 2)


    def test_phase1_reports_all_cells_not_best(self):
        from chan_trade_of.audit_p1 import audit_phase1

        rng = np.random.default_rng(0)
        rows = []
        for i in range(300):
            vol = float(10 + (i % 3) * 40 + rng.random())
            dlt = float(1 + (i % 3) * 20 + rng.random())
            hhi = 0.01 + 0.02 * rng.random()
            rows.append(
                {
                    "fx_id": str(i),
                    "fx_side": "BOTTOM" if i % 2 == 0 else "TOP",
                    "T_FX_VISIBLE": f"2026-07-{(i % 28) + 1:02d} 00:00:00+00:00",
                    "kline_delta": dlt,
                    "kline_volume": vol,
                    "hhi": hhi,
                    "push": 1.0 / hhi + rng.random(),
                    "leak": 0,
                }
            )
        out = audit_phase1(rows)
        self.assertEqual(len(out["cells"]), 9)
        self.assertNotIn("absorption_flag", json.dumps(out))

    def test_phase2_exits_and_no_b1(self):
        from chan_trade_of.audit_p2 import audit_phase2

        rng = np.random.default_rng(1)
        rows = []
        for i in range(400):
            vol = float(20 + rng.random() * 80)
            dlt = float(5 + rng.random() * 40)
            nlev = float(50 + rng.integers(0, 400))
            hhi = 0.02 + rng.random() * 0.03
            rows.append(
                {
                    "fx_id": str(i),
                    "fx_side": "BOTTOM" if i % 2 == 0 else "TOP",
                    "T_FX_VISIBLE": f"2026-07-{(i % 28) + 1:02d} 12:00:00+00:00",
                    "kline_delta": dlt,
                    "kline_volume": vol,
                    "hhi": hhi,
                    "push": 2.0 - 40 * hhi + rng.random(),
                    "n_levels": nlev,
                    "mid_range": float(40 + rng.random() * 80),
                    "leak": 0,
                }
            )
        out = audit_phase2(rows)
        self.assertIn(out["kind"], {"MECHANISM_STABLE", "CONDITIONAL_MECHANISM", "ARTIFACT", "CLOCK"})
        self.assertNotIn("absorption_flag", json.dumps(out))
        self.assertNotIn("label_B2", json.dumps(out))
        self.assertEqual(out["gates"][-1]["name"], "M4")
