from datetime import datetime, timedelta
import itertools
from pathlib import Path
import tempfile
import unittest

from .wp_bak import DATE_TIME_RE, delete_too_old, get_backup_list, make_timedelta


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

        t = make_timedelta('1m')
        self.assertEqual(t, timedelta(minutes=1))

    def test_datetime_re(self):
        self.assertIsNone(DATE_TIME_RE.fullmatch('202-04-05-11-50-00'))
        self.assertIsNone(DATE_TIME_RE.fullmatch('2021-4-05-11-50-00'))
        self.assertIsNone(DATE_TIME_RE.fullmatch('2021-04-05-11-50-00-more'))
        self.assertIsNone(DATE_TIME_RE.fullmatch('extra-2021-04-05-11-50-00'))
        self.assertIsNotNone(DATE_TIME_RE.fullmatch('2021-04-05-11-50-00'))

    def test_delete_too_old(self):
        # First create a temp dir for testing and then add some fake backups under that.
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            backups = [
                base_path / '2021-04-02-11-00-00',
                base_path / '2021-04-03-11-00-00',
                base_path / '2021-04-04-11-00-00',
                base_path / '2021-04-05-11-00-00']
            for backup in backups:
                backup.mkdir()
                (backup / 'files.tar.gz').touch()
                (backup / 'dbdump.sql.gz').touch()

            delete_too_old(base_path, datetime(2021, 4, 5, 11), timedelta(days=2))
            remaining = list(base_path.iterdir())

            self.assertEqual(set(remaining), set(backups[-2:]))

    def test_get_backup_list(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            backups = [
                base_path / '2021-04-02-11-00-00',
                base_path / '2021-04-03-11-00-00',
                base_path / '2021-04-04-11-00-00',
                base_path / '2021-04-05-11-00-00']
            others = [
                base_path / 'foo',
                base_path / '2021-04-03-11-00-00-copy']
            for dir in itertools.chain(backups, others):
                dir.mkdir()

            self.assertEqual(get_backup_list(base_path), backups)

