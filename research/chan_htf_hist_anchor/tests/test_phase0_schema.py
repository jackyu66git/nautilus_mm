import unittest

from chan_htf_hist_anchor.phase0_schema import (
    FORBIDDEN_LEDGER_KEYS,
    REPORT_FIELDS,
    assert_no_htf_bsp,
    is_historical,
    rail_side,
)


class HistAnchorSchemaTest(unittest.TestCase):
    def test_living_box_is_not_historical(self):
        self.assertFalse(is_historical(has_next=False, t_complete=1, t_b1=2))
        self.assertFalse(is_historical(has_next=True, t_complete=2, t_b1=2))
        self.assertFalse(is_historical(has_next=True, t_complete=3, t_b1=2))
        self.assertTrue(is_historical(has_next=True, t_complete=1, t_b1=2))

    def test_rail_side_no_percent(self):
        self.assertEqual(rail_side(101.0, 109.0, 100.0), "ABOVE")
        self.assertEqual(rail_side(90.0, 95.0, 100.0), "BELOW")
        self.assertEqual(rail_side(99.0, 101.0, 100.0), "CONTACT")
        self.assertEqual(rail_side(100.0, 110.0, 100.0), "CONTACT")
        self.assertEqual(rail_side(90.0, 100.0, 100.0), "CONTACT")

    def test_htf_bsp_and_near_are_pollution(self):
        self.assertIn("HTF_B1", FORBIDDEN_LEDGER_KEYS)
        self.assertIn("NEAR", FORBIDDEN_LEDGER_KEYS)
        self.assertIn("pos", FORBIDDEN_LEDGER_KEYS)
        with self.assertRaises(ValueError):
            assert_no_htf_bsp({"LTF_B1": 1, "HTF_B1": 1})
        with self.assertRaises(ValueError):
            assert_no_htf_bsp({"LTF_B1": 1, "b1_b2_rate": 0.2})
        assert_no_htf_bsp({"LTF_B1": 1, "side_zg": "CONTACT"})

    def test_report_fields_locked(self):
        self.assertIn("T_ZS_COMPLETE", REPORT_FIELDS)
        self.assertIn("NO_HIST_ANCHOR", REPORT_FIELDS)
        self.assertNotIn("pos", REPORT_FIELDS)
        from chan_htf_hist_anchor.audit_p0 import audit_phase0

        out = audit_phase0([])
        self.assertEqual(out["kind"], "CLOCK")
        self.assertIn("Q4", out["blocked"])
        self.assertNotIn("b1_b2_rate", str(out))


if __name__ == "__main__":
    unittest.main()
