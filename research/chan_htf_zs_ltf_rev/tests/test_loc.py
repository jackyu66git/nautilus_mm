import unittest

from chan_htf_zs_ltf_rev.scan import flipped, zs_loc


class ZsLocTest(unittest.TestCase):
    def test_inside_boundary_away(self):
        self.assertEqual(zs_loc(102.0, 108.0, 110.0, 100.0), "A_INSIDE")
        self.assertEqual(zs_loc(100.0, 105.0, 110.0, 100.0), "B_BOUNDARY")
        self.assertEqual(zs_loc(111.0, 120.0, 110.0, 100.0), "C_AWAY")
        self.assertEqual(zs_loc(80.0, 90.0, 110.0, 100.0), "C_AWAY")

    def test_flip_needs_both_dirs(self):
        self.assertTrue(flipped("UP", "DOWN"))
        self.assertFalse(flipped("UP", "UP"))
        self.assertFalse(flipped(None, "DOWN"))


if __name__ == "__main__":
    unittest.main()
