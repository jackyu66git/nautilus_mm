import unittest

from chanlun.core.ChanEnum import Chan_BSP_TYPE
from chan_1st_point_fate.scan import _FIRST


class FirstObjectTest(unittest.TestCase):
    def test_only_engine_first_types(self):
        self.assertEqual(_FIRST[Chan_BSP_TYPE.B1], "B1")
        self.assertEqual(_FIRST[Chan_BSP_TYPE.S1], "S1")
        self.assertNotIn(Chan_BSP_TYPE.B2, _FIRST)
        self.assertNotIn(Chan_BSP_TYPE.B3, _FIRST)


if __name__ == "__main__":
    unittest.main()
