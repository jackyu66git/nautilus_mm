import unittest

from chan_setup_strata.schema import bi_state, space_rel
from chan_setup_strata.tables import _table, assign_x, build_tables


class StrataContractTest(unittest.TestCase):
    def test_space_uses_zg_zd_not_gg_dd(self):
        leftover = [
            {
                "T_ZS_COMPLETE": "2026-01-01 00:00:00+00:00",
                "side_zg": "BELOW",
                "side_zd": "BELOW",
                "side_gg": "CONTACT",
                "side_dd": "CONTACT",
            }
        ]
        self.assertEqual(space_rel(leftover), "BELOW_BOX")

    def test_latest_leftover_wins(self):
        leftover = [
            {
                "T_ZS_COMPLETE": "2026-01-01 00:00:00+00:00",
                "side_zg": "ABOVE",
                "side_zd": "ABOVE",
            },
            {
                "T_ZS_COMPLETE": "2026-06-01 00:00:00+00:00",
                "side_zg": "BELOW",
                "side_zd": "BELOW",
            },
        ]
        self.assertEqual(space_rel(leftover), "BELOW_BOX")

    def test_contact_on_zg_or_zd(self):
        self.assertEqual(
            space_rel([{"T_ZS_COMPLETE": "t", "side_zg": "CONTACT", "side_zd": "BELOW"}]),
            "CONTACT_BOX",
        )

    def test_bi_state_not_merged(self):
        self.assertEqual(bi_state("UP", True), "UP_SURE")
        self.assertEqual(bi_state("UP", False), "UP_UNSURE")
        self.assertEqual(bi_state("DOWN", False), "DOWN_UNSURE")
        self.assertEqual(bi_state(None, True), "BI_DIR_NONE")

    def test_assign_x_from_birth_only(self):
        birth = {
            "htf_anchor_count": 3,
            "htf_leftover": [
                {"T_ZS_COMPLETE": "2026-01-01 00:00:00+00:00", "side_zg": "ABOVE", "side_zd": "ABOVE"}
            ],
            "ltf_bi_dir": "DOWN",
            "ltf_bi_sure": False,
            "ltf_fx": "TOP",
        }
        x = assign_x(birth)
        self.assertEqual(x["anchor_n"], 3)
        self.assertEqual(x["space_rel"], "ABOVE_BOX")
        self.assertEqual(x["bi_state"], "DOWN_UNSURE")
        self.assertEqual(x["fx_side"], "TOP")
        self.assertNotIn("outcome_class", x)

    def test_four_tables_only_and_no_hit_rate_key(self):
        rows = [
            {
                "anchor_n": 1,
                "space_rel": "BELOW_BOX",
                "bi_state": "UP_UNSURE",
                "fx_side": "BOTTOM",
                "outcome_class": "DISSOLVES",
            },
            {
                "anchor_n": 1,
                "space_rel": "BELOW_BOX",
                "bi_state": "DOWN_UNSURE",
                "fx_side": "TOP",
                "outcome_class": "REVERSES",
            },
        ]
        tables = build_tables(rows)
        self.assertEqual(
            set(tables),
            {"htf_leftover_count", "space_relation", "bi_state", "fractal_direction"},
        )
        blob = str(tables)
        self.assertNotIn("hit_rate", blob)
        self.assertNotIn("p_value", blob)
        self.assertNotIn("NEW_SETUP", blob)
        self.assertNotIn("four_way", blob)

    def test_anchor_levels_are_raw_ints(self):
        rows = [
            {
                "anchor_n": 1,
                "space_rel": "BELOW_BOX",
                "bi_state": "UP_UNSURE",
                "fx_side": "BOTTOM",
                "outcome_class": "DISSOLVES",
            },
            {
                "anchor_n": 10,
                "space_rel": "BELOW_BOX",
                "bi_state": "UP_UNSURE",
                "fx_side": "BOTTOM",
                "outcome_class": "DISSOLVES",
            },
        ]
        tab = _table(rows, "anchor_n", None)
        self.assertEqual([r["level"] for r in tab], [1, 10])


if __name__ == "__main__":
    unittest.main()
