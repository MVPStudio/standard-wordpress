import unittest
from datetime import timedelta
from .wp_bak import make_timedelta


class TestWpBack(unittest.TestCase):
    def test_make_timedelta(self):
        t = make_timedelta('2h7s')
        self.assertEqual(t, timedelta(hours=2, seconds=7))

        t = make_timedelta('2h 7s')
        self.assertEqual(t, timedelta(hours=2, seconds=7))

        t = make_timedelta(' 2 h 7  s  ')
        self.assertEqual(t, timedelta(hours=2, seconds=7))

        t = make_timedelta('1h6s5s2d')
        self.assertEqual(t, timedelta(days=2, hours=1, seconds=6 + 5))
