import unittest

from chanlun.core.ChanEnum import Chan_BI_DIR
from chan_2nd_point_fate.detect import classify_second


class _Bi:
    def __init__(self, low, high, dir_, sure=True, nxt=None, macd=1.0):
        self.low = low
        self.high = high
        self.dir = dir_
        self.is_sure = sure
        self.next = nxt
        self.macd_hist = macd
        self.start_time = "x"


class _Zs:
    def __init__(self, enter, members):
        self.bi_list = members
        members[0].pre = enter


class _Tf:
    def check_bi_div(self, zs, leave):
        enter = zs.bi_list[0].pre
        return abs(leave.macd_hist) - abs(enter.macd_hist) < 0


class SecondDetectTest(unittest.TestCase):
    def test_b2_higher_low_after_first(self):
        sec = _Bi(102, 110, Chan_BI_DIR.DOWN)
        mid = _Bi(100, 120, Chan_BI_DIR.UP, nxt=sec)
        leave = _Bi(90, 100, Chan_BI_DIR.DOWN, nxt=mid, macd=0.5)
        enter = _Bi(80, 95, Chan_BI_DIR.DOWN, macd=2.0)
        zs = _Zs(enter, [_Bi(1, 2, Chan_BI_DIR.UP), _Bi(1, 2, Chan_BI_DIR.DOWN), _Bi(1, 2, Chan_BI_DIR.UP)])
        hit = classify_second(_Tf(), zs, leave, "DOWN")
        self.assertEqual(hit["kind"], "B2")

    def test_no_first_is_not_b2(self):
        sec = _Bi(102, 110, Chan_BI_DIR.DOWN)
        mid = _Bi(100, 120, Chan_BI_DIR.UP, nxt=sec)
        leave = _Bi(90, 100, Chan_BI_DIR.DOWN, nxt=mid, macd=3.0)
        enter = _Bi(80, 95, Chan_BI_DIR.DOWN, macd=1.0)
        zs = _Zs(enter, [_Bi(1, 2, Chan_BI_DIR.UP)])
        hit = classify_second(_Tf(), zs, leave, "DOWN")
        self.assertEqual(hit["kind"], "NO_FIRST")


if __name__ == "__main__":
    unittest.main()
