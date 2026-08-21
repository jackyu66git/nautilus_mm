import unittest

from chanlun.core.ChanEnum import Chan_BI_DIR, Chan_ZS_DIR
from chan_3rd_point.detect import classify_pullback, first_leave


class _Klc:
    def __init__(self, high, low):
        self.high = high
        self.low = low


class _Bi:
    def __init__(self, start, low, high, dir_, sure=True, nxt=None):
        self.start_time = start
        self.low = low
        self.high = high
        self.dir = dir_
        self.is_sure = sure
        self.next = nxt
        self.end_klc = _Klc(high, low)


class _Zs:
    def __init__(self, bis, zg, zd):
        self.bi_list = bis
        self.zg = zg
        self.zd = zd
        self.start_bi = bis[0]
        self.dir = Chan_ZS_DIR.UP


class ThirdDetectTest(unittest.TestCase):
    def test_b3_when_pullback_stays_above_zg(self):
        pb = _Bi("p", 111, 120, Chan_BI_DIR.DOWN)
        leave = _Bi("l", 112, 130, Chan_BI_DIR.UP, nxt=pb)
        m3 = _Bi("3", 100, 110, Chan_BI_DIR.DOWN, nxt=leave)
        m2 = _Bi("2", 101, 109, Chan_BI_DIR.UP, nxt=m3)
        m1 = _Bi("1", 100, 108, Chan_BI_DIR.DOWN, nxt=m2)
        zs = _Zs([m1, m2, m3], zg=110, zd=100)
        leave_found, side = first_leave(zs)
        self.assertEqual(side, "UP")
        self.assertIs(leave_found, leave)
        hit = classify_pullback(leave, 110, 100, "UP")
        self.assertEqual(hit["kind"], "B3")

    def test_reentry_on_pullback_is_not_b3(self):
        pb = _Bi("p", 105, 120, Chan_BI_DIR.DOWN)
        leave = _Bi("l", 112, 130, Chan_BI_DIR.UP, nxt=pb)
        hit = classify_pullback(leave, 110, 100, "UP")
        self.assertEqual(hit["kind"], "PULLBACK_IN")

    def test_unfinished_pullback_is_not_visible(self):
        pb = _Bi("p", 111, 120, Chan_BI_DIR.DOWN, sure=False)
        leave = _Bi("l", 112, 130, Chan_BI_DIR.UP, nxt=pb)
        self.assertIsNone(classify_pullback(leave, 110, 100, "UP"))


if __name__ == "__main__":
    unittest.main()
