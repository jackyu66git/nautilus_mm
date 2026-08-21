import unittest

import pandas as pd

from chan_desk_replay.audit import audit_tape
from chan_desk_replay.schema import FORBIDDEN_LEDGER_KEYS, SMC_STATE, assert_clean


def _row(t, **kw):
    rec = {
        "t": t,
        "open_ts": t,
        "htf_anchor_count": 0,
        "htf_leftover": [],
        "htf_living": "none",
        "ltf_bi_dir": "DOWN",
        "ltf_bi_sure": True,
        "ltf_fx": "BOTTOM",
        "ltf_fx_id": "x",
        "T_FX_VISIBLE": t,
        "b1_lock": False,
        "b1_lock_id": None,
        "of_kline_delta": 1.0,
        "of_kline_volume": 2.0,
        "of_trade_status": "ok",
        "of_trade_n": 3,
        "of_trade_delta": 0.1,
        "of_hhi": 0.2,
        "of_push": 0.3,
        "of_speed": 0.4,
        "of_window_end": t,
        "smc_state": SMC_STATE,
    }
    rec.update(kw)
    return rec


class DeskReplaySchemaTest(unittest.TestCase):
    def test_forbidden_subjective_keys(self):
        for k in ("allow", "Entry", "Stop", "MFE", "MAE", "of_support", "B2", "LTF_B2"):
            self.assertIn(k, FORBIDDEN_LEDGER_KEYS)
        with self.assertRaises(ValueError):
            assert_clean({"t": "1", "smc_state": SMC_STATE, "allow": True})
        with self.assertRaises(ValueError):
            assert_clean({"t": "1", "smc_state": "sweep"})
        assert_clean(_row("2026-07-13 15:15:00+00:00"))

    def test_smc_must_be_undefined(self):
        with self.assertRaises(ValueError):
            assert_clean(_row("2026-07-13 15:15:00+00:00", smc_state="BOS"))

    def test_audit_rejects_future_leftover(self):
        ts = pd.date_range("2026-05-21 10:45:00", periods=8600, freq="15min", tz="UTC")
        extra = [_row(str(t)) for t in ts]
        extra[100]["htf_leftover"] = [{"T_ZS_COMPLETE": str(ts[100] + pd.Timedelta(hours=1))}]
        extra[100]["htf_anchor_count"] = 1
        out = audit_tape(extra)
        self.assertEqual(out["kind"], "LEAK")
        self.assertEqual(out["decision"], "FAIL")


if __name__ == "__main__":
    unittest.main()
