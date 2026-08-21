import unittest

from chan_htf_hist_anchor.audit_q4 import audit_q4, collapse_to_b1
from chan_htf_hist_anchor.phase0_schema import FORBIDDEN_LEDGER_KEYS, assert_no_htf_bsp


def _pair(b1, zs, n, side_zg="BELOW", side_zd="BELOW", side_gg="BELOW", side_dd="BELOW"):
    return {
        "LTF_B1": b1,
        "T_LTF_B1": f"{b1}+00:00",
        "B1_bar": b1,
        "leave_low": 100.0,
        "leave_high": 101.0,
        "zs_id": zs,
        "T_ZS_COMPLETE": zs,
        "side_zg": side_zg,
        "side_zd": side_zd,
        "side_gg": side_gg,
        "side_dd": side_dd,
        "NO_HIST_ANCHOR": False,
        "n_hist_zs": n,
    }


class Q4UnitTest(unittest.TestCase):
    def test_collapse_is_b1_not_pair(self):
        pairs = [
            _pair("B1-a", "z1", 2, side_zg="BELOW"),
            _pair("B1-a", "z2", 2, side_zd="CONTACT"),
            _pair("B1-b", "z1", 1, side_gg="ABOVE"),
        ]
        rows = collapse_to_b1(pairs, {"B1-a": True, "B1-b": False})
        self.assertEqual([r["LTF_B1"] for r in rows], ["B1-a", "B1-b"])
        self.assertEqual(rows[0]["anchor_count_at_B1"], 2)
        self.assertTrue(rows[0]["contact_any"])
        self.assertTrue(rows[0]["zd_contact_any"])
        self.assertFalse(rows[0]["zg_contact_any"])
        self.assertFalse(rows[1]["contact_any"])
        self.assertTrue(rows[0]["LTF_B2"])
        self.assertFalse(rows[1]["LTF_B2"])

    def test_pair_rows_fail_unit_gate(self):
        pairs = [_pair("B1-a", "z1", 2), _pair("B1-a", "z2", 2)]
        for r in pairs:
            r["LTF_B2"] = True
            r["anchor_count_at_B1"] = 2
            r["contact_any"] = False
            r["zg_contact_any"] = False
            r["zd_contact_any"] = False
            r["gg_contact_any"] = False
            r["dd_contact_any"] = False
        out = audit_q4(pairs, {2: {"rate": 0.1, "n_bars": 10, "n_contact": 1}})
        self.assertEqual(out["kind"], "CLOCK")
        self.assertEqual(out["gates"][0]["verdict"], "FAIL")

    def test_all_b2_is_no_fate_contrast(self):
        rows = collapse_to_b1(
            [_pair("B1-a", "z1", 1, side_zg="CONTACT"), _pair("B1-b", "z1", 1)],
            {"B1-a": True, "B1-b": True},
        )
        out = audit_q4(rows, {1: {"rate": 0.2, "n_bars": 50, "n_contact": 10}})
        self.assertEqual(out["decision"], "FAIL")
        self.assertEqual(out["kind"], "NO_FATE_CONTRAST")
        self.assertEqual(out["n_events"], 2)
        self.assertIn("MFE", out["blocked"])
        c2 = [g for g in out["gates"] if g["name"] == "C2"][0]
        self.assertEqual(c2["verdict"], "PASS")

    def test_b2_variation_keeps_cells(self):
        rows = collapse_to_b1(
            [_pair("B1-a", "z1", 1, side_zg="CONTACT"), _pair("B1-b", "z1", 1)],
            {"B1-a": True, "B1-b": False},
        )
        out = audit_q4(rows, {1: {"rate": 0.05, "n_bars": 40, "n_contact": 2}})
        self.assertEqual(out["decision"], "PASS")
        self.assertEqual(out["kind"], "STRUCTURE_CONTRAST")
        c3 = [g for g in out["gates"] if g["name"] == "C3"][0]
        self.assertIn("yes/yes=1", c3["detail"])
        self.assertIn("no/no=1", c3["detail"])

    def test_forbidden_q4_keys(self):
        self.assertIn("MFE", FORBIDDEN_LEDGER_KEYS)
        self.assertIn("MAE", FORBIDDEN_LEDGER_KEYS)
        self.assertIn("combo_score", FORBIDDEN_LEDGER_KEYS)
        self.assertIn("pos", FORBIDDEN_LEDGER_KEYS)
        self.assertIn("NEAR", FORBIDDEN_LEDGER_KEYS)
        with self.assertRaises(ValueError):
            assert_no_htf_bsp({"LTF_B1": "x", "MFE": 1})
        with self.assertRaises(ValueError):
            collapse_to_b1([_pair("B1-a", "z1", 1)], {"B1-a": True})[0].update({"Entry": 1})
            assert_no_htf_bsp({"LTF_B1": "x", "Entry": 1})


if __name__ == "__main__":
    unittest.main()
