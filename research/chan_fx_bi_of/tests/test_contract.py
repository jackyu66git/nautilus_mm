import unittest

from chan_fx_bi_of.frozen_config import assert_clean


class FxBiContractTest(unittest.TestCase):
    def test_b1_forbidden(self):
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "label_B1": 1})
        with self.assertRaises(ValueError):
            assert_clean({"fx_id": "x", "B2": 1})
        assert_clean({"fx_id": "x", "of_delta_forming": 1.0, "label_bi_endpoint": 1})


if __name__ == "__main__":
    unittest.main()
