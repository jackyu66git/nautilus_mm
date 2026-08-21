import unittest

from chan_3buy_ema52.scan import _entered, _next_pullback


class ThirdEmaTest(unittest.TestCase):
    def test_entered_includes_cross_and_near(self):
        self.assertTrue(_entered(0.2, False))
        self.assertTrue(_entered(2.0, True))
        self.assertFalse(_entered(0.9, False))

    def test_next_pullback_is_after_t3(self):
        low = [10, 9, 8, 7, 6, 5, 6]
        high = [11] * 7
        self.assertEqual(_next_pullback(0, "B3", low, high, 7), 6)


if __name__ == "__main__":
    unittest.main()
