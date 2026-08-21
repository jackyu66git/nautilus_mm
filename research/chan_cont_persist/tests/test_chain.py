import unittest

import numpy as np

from chan_cont_persist.scan import chain_ok


class ChainTest(unittest.TestCase):
    def test_buy_chain_stops(self):
        high = np.array([10.0, 11.0, 12.0, 11.5, 13.0])
        low = np.array([9.0, 9.5, 10.0, 10.0, 10.5])
        self.assertTrue(chain_ok(high, low, 0, "BUY", 1))
        self.assertTrue(chain_ok(high, low, 0, "BUY", 2))
        self.assertFalse(chain_ok(high, low, 0, "BUY", 3))

    def test_h2_requires_h1(self):
        high = np.array([10.0, 9.0, 12.0])
        low = np.zeros(3)
        self.assertFalse(chain_ok(high, low, 0, "BUY", 1))
        self.assertFalse(chain_ok(high, low, 0, "BUY", 2))


if __name__ == "__main__":
    unittest.main()
