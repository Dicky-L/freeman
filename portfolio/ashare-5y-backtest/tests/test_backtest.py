import unittest
from backtest import valid_symbol
class Boards(unittest.TestCase):
    def test_whitelist(self):
        for x in ("000625","002714","300394","301012","603606"):self.assertTrue(valid_symbol(x))
        for x in ("688001","830001","920001","abc"):self.assertFalse(valid_symbol(x))
if __name__=="__main__":unittest.main()
