import unittest

from chan_ema52_state.scan import _bucket
from chan_ema52_state.state import market_state


class _Zs:
    def __init__(self, zg, zd, nxt=None):
        self.zg = zg
        self.zd = zd
        self.next = nxt
        self.start_bi = type("B", (), {"start_time": "a"})()


class StateTest(unittest.TestCase):
    def test_inside_is_range_not_trend(self):
        zs = _Zs(110, 100)
        self.assertEqual(market_state([zs], 105, 106, 104), "RANGE")

    def test_overlap_leave_is_transition(self):
        zs = _Zs(110, 100)
        self.assertEqual(market_state([zs], 112, 113, 108), "TRANSITION")

    def test_full_bar_above_is_trend_up(self):
        zs = _Zs(110, 100)
        self.assertEqual(market_state([zs], 120, 121, 119), "TREND_UP")

    def test_cross_outranks_near(self):
        self.assertEqual(_bucket(True, 0.1), "CROSS")
        self.assertEqual(_bucket(False, 0.2), "NEAR")
        self.assertEqual(_bucket(False, 0.8), "MID")
        self.assertEqual(_bucket(False, 1.5), "FAR")


if __name__ == "__main__":
    unittest.main()
