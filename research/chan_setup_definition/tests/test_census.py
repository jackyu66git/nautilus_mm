import unittest

from chan_setup_definition.census import scan_candidates
from chan_setup_definition.schema import FORBIDDEN_CENSUS_KEYS, assert_census_clean


def _row(t, fx_id, leftover, fx="BOTTOM", t_fx=None, **kw):
    rec = {
        "t": t,
        "htf_anchor_count": leftover,
        "ltf_fx": fx,
        "ltf_fx_id": fx_id,
        "T_FX_VISIBLE": t_fx if t_fx is not None else t,
        "b1_lock": False,
        "of_hhi": 9.9,
        "smc_state": "UNDEFINED",
        "htf_living": "FORMING",
    }
    rec.update(kw)
    return rec


class CensusFirstSeenTest(unittest.TestCase):
    def test_first_seen_is_tape_row_not_t_fx_visible(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", "A", 1, t_fx="2026-01-01 03:00:00+00:00"),
            _row("2026-01-01 00:15:00+00:00", "A", 1, t_fx="2026-01-01 04:00:00+00:00"),
        ]
        events = scan_candidates(rows)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["T_SETUP_VISIBLE"], "2026-01-01 00:00:00+00:00")
        self.assertEqual(events[0]["tape_row"], 0)
        self.assertNotEqual(events[0]["T_SETUP_VISIBLE"], rows[0]["T_FX_VISIBLE"])

    def test_identity_consumed_when_first_seen_has_no_leftover(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", "A", 0),
            _row("2026-01-01 00:15:00+00:00", "A", 1),
            _row("2026-01-01 00:30:00+00:00", "B", 1),
        ]
        events = scan_candidates(rows)
        ids = [e["setup_id"] for e in events]
        self.assertEqual(ids, ["B"])
        self.assertEqual(events[0]["T_SETUP_VISIBLE"], "2026-01-01 00:30:00+00:00")

    def test_same_id_contiguous_is_one_setup(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", "A", 1),
            _row("2026-01-01 00:15:00+00:00", "A", 1),
            _row("2026-01-01 00:30:00+00:00", "A", 1),
        ]
        events = scan_candidates(rows)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["duration_bars"], 3)
        self.assertEqual(events[0]["duration_hours"], 0.5)
        self.assertEqual(events[0]["T_SETUP_END"], "2026-01-01 00:30:00+00:00")

    def test_reappearance_after_gap_does_not_clone(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", "A", 1),
            _row("2026-01-01 00:15:00+00:00", "B", 1),
            _row("2026-01-01 00:30:00+00:00", "A", 1),
        ]
        events = scan_candidates(rows)
        self.assertEqual([e["setup_id"] for e in events], ["A", "B"])
        self.assertEqual(events[0]["duration_bars"], 1)

    def test_census_record_has_no_outcome_or_of(self):
        events = scan_candidates([_row("2026-01-01 00:00:00+00:00", "A", 1)])
        assert_census_clean(events[0])
        for k in FORBIDDEN_CENSUS_KEYS:
            self.assertNotIn(k, events[0])


if __name__ == "__main__":
    unittest.main()
