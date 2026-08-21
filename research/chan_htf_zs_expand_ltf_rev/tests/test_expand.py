import unittest

from chan_htf_zs_expand_ltf_rev.scan import contrast_kind, process_state


class ExpandStateTest(unittest.TestCase):
    def test_process_state(self):
        self.assertEqual(process_state(None, None), "NONE")
        self.assertEqual(process_state(None, {"zs_id": "a", "n_bis": 3}), "NEW_BOX")
        self.assertEqual(
            process_state({"zs_id": "a", "n_bis": 3}, {"zs_id": "a", "n_bis": 5}),
            "EXPAND",
        )
        self.assertEqual(
            process_state({"zs_id": "a", "n_bis": 5}, {"zs_id": "a", "n_bis": 5}),
            "STABLE",
        )

    def test_contrast_rule(self):
        overall = 0.047
        flat = [
            {"n": 100, "rev_share": 0.045},
            {"n": 100, "rev_share": 0.050},
        ]
        self.assertEqual(contrast_kind(flat, overall), "NO_STATE_CONTRAST")
        thin = [{"n": 10, "rev_share": 0.2}, {"n": 10, "rev_share": 0.0}]
        self.assertEqual(contrast_kind(thin, overall), "SAMPLE_INSUFFICIENT")
