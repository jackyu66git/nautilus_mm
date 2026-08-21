import unittest

from chan_htf_zs_ltf_b1.audit_p0 import audit_phase0
from chan_htf_zs_ltf_b1.frozen_config import assert_clean
from chan_htf_zs_ltf_b1.phase0_schema import (
    FORBIDDEN_LEDGER_KEYS,
    Phase0Row,
    REPORT_FIELDS,
    assert_no_htf_bsp,
    living_at_b1,
    spatial_bucket,
)


class Phase0SchemaTest(unittest.TestCase):
    def test_report_fields_locked(self):
        self.assertEqual(
            REPORT_FIELDS,
            (
                "T_HTF_ZS_VISIBLE",
                "T_LTF_B1",
                "delta_t",
                "ZS_birth_bar",
                "B1_bar",
                "ZS_valid_at_B1",
                "zg_at_visibility",
                "zd_at_visibility",
                "zg_at_B1",
                "zd_at_B1",
            ),
        )
        self.assertTrue(set(REPORT_FIELDS).issubset(Phase0Row.__dataclass_fields__))

    def test_htf_bsp_keys_are_pollution(self):
        self.assertEqual(FORBIDDEN_LEDGER_KEYS, {"HTF_B1", "HTF_B2", "HTF_BSP"})
        with self.assertRaises(ValueError) as ctx:
            assert_no_htf_bsp({"LTF_B1": 1, "HTF_B1": 1})
        self.assertIn("HTF_B1", str(ctx.exception))
        assert_no_htf_bsp({"LTF_B1": 1, "T_LTF_B1": 2})

    def test_living_not_leftover(self):
        self.assertTrue(living_at_b1(present=True, has_next=False, zg_zd_unchanged=True))
        self.assertFalse(living_at_b1(present=True, has_next=True, zg_zd_unchanged=True))
        self.assertFalse(living_at_b1(present=False, has_next=False, zg_zd_unchanged=True))
        self.assertFalse(living_at_b1(present=True, has_next=False, zg_zd_unchanged=False))

    def test_spatial_three_buckets_no_percent(self):
        self.assertEqual(spatial_bucket(101.0, 109.0, 100.0, 110.0), "INSIDE")
        self.assertEqual(spatial_bucket(90.0, 95.0, 100.0, 110.0), "OUTSIDE")
        self.assertEqual(spatial_bucket(111.0, 120.0, 100.0, 110.0), "OUTSIDE")
        self.assertEqual(spatial_bucket(99.0, 101.0, 100.0, 110.0), "BOUNDARY_CONTACT")
        self.assertEqual(spatial_bucket(109.0, 111.0, 100.0, 110.0), "BOUNDARY_CONTACT")
        self.assertEqual(spatial_bucket(100.0, 110.0, 100.0, 110.0), "BOUNDARY_CONTACT")

    def test_phase0_forbids_b2_rate_and_htf_bsp(self):
        with self.assertRaises(ValueError):
            assert_clean({"LTF_B1": 1, "b1_b2_rate": 0.5})
        with self.assertRaises(ValueError):
            assert_no_htf_bsp({"LTF_B1": 1, "HTF_B1": 1})
        out = audit_phase0([])
        self.assertEqual(out["kind"], "CLOCK")
        dumped = str(out)
        self.assertNotIn("b1_b2_rate", dumped)
        self.assertNotIn("win_rate", dumped)


if __name__ == "__main__":
    unittest.main()
