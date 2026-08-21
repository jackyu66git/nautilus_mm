import unittest

from chan_setup_outcome.scan import detect_event, scan_one, summarize
from chan_setup_outcome.schema import classify


def _row(t, fx_id="A", fx="BOTTOM", bi_dir="UP", bi_sure=False, b1=False):
    return {
        "t": t,
        "ltf_fx_id": fx_id,
        "ltf_fx": fx,
        "ltf_bi_dir": bi_dir,
        "ltf_bi_sure": bi_sure,
        "b1_lock": b1,
    }


class OutcomeContractTest(unittest.TestCase):
    def test_fx_alternate_is_not_reverse(self):
        self.assertEqual(classify("FX_IDENTITY_CHANGE", False), "DISSOLVES")
        self.assertEqual(classify("FX_IDENTITY_CHANGE", True), "NEXT_EVENT")
        self.assertEqual(classify("BI_DIR_CHANGE", False), "REVERSES")

    def test_same_bar_dir_beats_fx(self):
        row = _row("2026-01-01 00:15:00+00:00", fx_id="B", bi_dir="DOWN", bi_sure=True)
        self.assertEqual(detect_event(row, "A", "UP", False), "BI_DIR_CHANGE")

    def test_later_b1_not_assigned_after_first_event(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", fx_id="A", bi_sure=False),
            _row("2026-01-01 00:15:00+00:00", fx_id="B", fx="TOP", bi_sure=False),
            _row("2026-01-01 00:30:00+00:00", fx_id="B", fx="TOP", b1=True),
        ]
        setup = {
            "setup_id": "A",
            "T_SETUP_VISIBLE": "2026-01-01 00:00:00+00:00",
            "tape_row": 0,
        }
        rec = scan_one(rows, setup)
        self.assertEqual(rec["outcome_event"], "FX_IDENTITY_CHANGE")
        self.assertEqual(rec["outcome_class"], "DISSOLVES")
        self.assertFalse(rec["label_b1"])
        self.assertEqual(rec["T_OUTCOME_VISIBLE"], "2026-01-01 00:15:00+00:00")

    def test_birth_bar_b1_is_not_label(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", fx_id="A", b1=True),
            _row("2026-01-01 00:15:00+00:00", fx_id="B", fx="TOP"),
        ]
        rec = scan_one(
            rows,
            {"setup_id": "A", "T_SETUP_VISIBLE": "2026-01-01 00:00:00+00:00", "tape_row": 0},
        )
        self.assertFalse(rec["label_b1"])

    def test_b1_on_outcome_bar_is_label(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", fx_id="A"),
            _row("2026-01-01 00:15:00+00:00", fx_id="B", fx="TOP", b1=True),
        ]
        rec = scan_one(
            rows,
            {"setup_id": "A", "T_SETUP_VISIBLE": "2026-01-01 00:00:00+00:00", "tape_row": 0},
        )
        self.assertTrue(rec["label_b1"])

    def test_censor_is_not_failure_class(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", fx_id="A"),
            _row("2026-01-01 00:15:00+00:00", fx_id="A"),
        ]
        rec = scan_one(
            rows,
            {"setup_id": "A", "T_SETUP_VISIBLE": "2026-01-01 00:00:00+00:00", "tape_row": 0},
        )
        self.assertEqual(rec["outcome_event"], "CENSOR")
        self.assertEqual(rec["outcome_class"], "CENSOR")
        self.assertEqual(rec["T_OUTCOME_VISIBLE"], "2026-01-01 00:15:00+00:00")

    def test_last_row_birth_is_clock_drop_not_new_class(self):
        rows = [_row("2026-01-01 00:00:00+00:00", fx_id="A")]
        rec = scan_one(
            rows,
            {"setup_id": "A", "T_SETUP_VISIBLE": "2026-01-01 00:00:00+00:00", "tape_row": 0},
        )
        self.assertIsNone(rec)

    def test_summary_has_no_hit_rate(self):
        rows = [
            _row("2026-01-01 00:00:00+00:00", fx_id="A"),
            _row("2026-01-01 00:15:00+00:00", fx_id="B", fx="TOP"),
        ]
        rec = scan_one(
            rows,
            {"setup_id": "A", "T_SETUP_VISIBLE": "2026-01-01 00:00:00+00:00", "tape_row": 0},
        )
        summary = summarize([rec])
        self.assertNotIn("hit_rate", summary)
        self.assertNotIn("success", summary)
        self.assertEqual(summary["label_b2"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
