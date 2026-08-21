import unittest

import numpy as np

from chan_fx_bi_trade_of.audit import audit, join_ledgers
from chan_fx_bi_trade_of.frozen_config import assert_clean


class FxBiTradeContractTest(unittest.TestCase):
    def test_b1_and_combo_forbidden(self):
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "B1": 1})
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "combo_score": 1})
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "absorption_flag": 1})
        assert_clean({"fx_id": "x", "hhi": 0.2, "push": 0.1, "label_bi_endpoint": 1})

    def test_join_mismatch_is_clock(self):
        trade = [
            {
                "fx_id": "a",
                "fx_side": "BOTTOM",
                "T_FX_VISIBLE": "2026-07-01 00:00:00+00:00",
                "mid_range": 10.0,
                "kline_delta": -1.0,
                "hhi": 0.1,
                "push": 0.2,
                "leak": 0,
                "retracted": False,
            }
        ]
        fx = [{"fx_id": "b", "fx_side": "BOTTOM", "label_bi_endpoint": 1}]
        rows, missing, extra, side = join_ledgers(trade, fx)
        out = audit(rows, missing, extra, side, require_baseline_n=False)
        self.assertEqual(out["kind"], "CLOCK")
        self.assertEqual(out["decision"], "FAIL")

    def test_delta_only_hhi_is_no_increment(self):
        rng = np.random.default_rng(1)
        trade, fx = [], []
        for i in range(200):
            is_bi = i < 80
            dlt = -80.0 - rng.random() * 20 if is_bi else -10.0 + rng.random() * 20
            rec_t = {
                "fx_id": str(i),
                "fx_side": "BOTTOM",
                "T_FX_VISIBLE": "2026-07-01 00:00:00+00:00",
                "mid_range": float(40 + rng.random() * 10),
                "kline_delta": dlt,
                "hhi": abs(dlt) / 500.0,
                "push": 0.5 + rng.random() * 0.01,
                "leak": 0,
                "retracted": False,
            }
            trade.append(rec_t)
            fx.append({"fx_id": str(i), "fx_side": "BOTTOM", "label_bi_endpoint": int(is_bi)})
        rows, missing, extra, side = join_ledgers(trade, fx)
        out = audit(rows, missing, extra, side, require_baseline_n=False)
        self.assertNotIn("B2", "".join(g["name"] for g in out["gates"]))
        self.assertIn(out["kind"], {"NO_INCREMENT", "CLOCK", "INDEPENDENT_STRUCTURE"})
        self.assertNotIn("combo_score", str(out))


if __name__ == "__main__":
    unittest.main()
