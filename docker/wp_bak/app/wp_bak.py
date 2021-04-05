#!/usr/bin/env python3
# Docker:
# docker build -t mvpstudio/wordpress-backup:v0001 .
# docker run -v `pwd`/src:/src -v `pwd`/dst:/dst -t mvpstudio/wordpress-backup:v0001

import argparse
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
from typing import List

#############################
# CONSTANTS
#############################

SRC_DIR=Path('/src')
DST_DIR=Path('/dst')
SHORT_DIR=DST_DIR.joinpath('shorts')
LONG_DIR=DST_DIR.joinpath('longs')

DATE_TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"
# regex that matches timestamps in DATE_TIME_FORMAT
DATE_TIME_RE = re.compile(r'\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}')

logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                   format='%(asctime)s %(levelname)-8s %(message)s')
log = logging.getLogger(__name__)

#############################
# FUNCTIONS
#############################

def make_timedelta(arg: str) -> timedelta:
    """Given a string holding values with suffixes like `d` for day, `h` for hour, `m` for minutes, and `s` for seconds
    return a timedelta with the corresponding value. For example, "1d 4h 3s" would be parsed into a timedelta with value
    1 day, 4 hours, and 3 seconds.
    """
    # Regular expression to look for integers followed by d, h, m, or s suffixes (for days, hours, minutes, and
    # seconds).
    hms_re = re.compile(r'\s*(\d+)\s*([dhms])\s*')

    units = {
        'd': timedelta(days=1),
        'h': timedelta(hours=1),
        'm': timedelta(minutes=1),
        's': timedelta(seconds=1)
    }

    result = timedelta(seconds=0)
    for m in hms_re.finditer(arg):
        unit = units[m.group(2)]
        result += int(m.group(1)) * unit

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Backs up a WordPress site')
    parser.add_argument('-b', '--backup_freq', type=make_timedelta, default=timedelta(days=1),
                       help='How frequently to make backups. This is a string with "d" indicating days, '
                       '"h" indicating hours, "m" indicating minutes, and "s" for seconds. Thus a '
                        'string like "2d4h7m" means "make a backup every 2 days, 4 hours and 7 minutes". '
                       'Default is 1 day.')
    parser.add_argument('--short_keep', type=make_timedelta, default=timedelta(days=7),
                        help='How long to keep every backup. Format is the same as for --backup_freq. '
                       'Default is 7 days.')
    parser.add_argument('-l', '--long_freq', type=make_timedelta, default=timedelta(days=7),
                        help='How frequently to make a "long" backup (see the main repo README for details). '
                        'Format is the same as for --backup_freq. Default is 7 days.')
    parser.add_argument('--long_keep', type=make_timedelta, default=timedelta(days=28),
                        help='How frequently to retain "long" backups (see the main repo README for details). '
                        'Format is the same as for --backup_freq. Default is 28 days.')
    parser.add_argument('--db_host', required=True, help='The hostname of the MySQL or MariaDb server')
    parser.add_argument('--db_user', required=True,
                        help='The username to use to connect to the MySQL or MariaDb server')
    parser.add_argument('--db_pass', required=True,
                        help='The password to use to connect to the MySQL or MariaDb server')

    log.info('Parsing command line: %s', sys.argv)
    parsed = parser.parse_args()

    error = False
    if parsed.backup_freq >= parsed.short_keep:
        log.error('--backup_freq must be less than --short_keep')
        error = True

    if parsed.backup_freq >= parsed.long_freq:
        log.error('--backup_freq must be less than --long_freq')

    if parsed.long_freq >= parsed.long_keep:
        log.error('--long_freq must be less than --long_keep')

    if error:
        parser.print_help()
        sys.exit(1)

    log.info('Settings:')
    log.info('backup_freq: %s', parsed.backup_freq)
    log.info('short_keep: %s', parsed.short_keep)
    log.info('long_freq: %s', parsed.long_freq)
    log.info('long_keep: %s', parsed.long_keep)

    return parsed


def dirname2age(now: datetime, dirname: str) -> timedelta:
    """Calculcates the age of a backup directory.

    Parameters
    ----------
    now : datetime
        The time to use as "now" for calculating item's age.

    dirname : string
        The name of the backup directory to calculate age of.
    """
    # Get age from archive-date string
    return now - datetime.strptime(dirname, DATE_TIME_FORMAT)

def get_backup_list(dir: Path) -> List[Path]:
    """Returns a sorted list of archive files from the specified directory.

    Parameters
    ----------
    dir : Path
        The directory to list.

    Returns
    -------
    A list of Path of all the directories that look like backups. Files and directories that don't match the backup
    directory naming scheme are ignored.
    """
    dirs = [x for x in dir.iterdir() if DATE_TIME_RE.fullmatch(x.name) is not None]
    dirs.sort()
    return dirs

def delete_too_old(dir: Path, now: datetime, cutoff: timedelta) -> None:
    """Deletes everything in the specified directory that is equal to or older than the cutoff.

    Parameters
    ----------
    dir : string, name of directory
        The directory to prune.

    now : datetime object
        The time to use as "now" for calculating item's age.

    cutoff : timedelta object
        The age, older than which, we delete the file.
    """
    backups = get_backup_list(dir)
    for backup in backups:
        if dirname2age(now, backup.name) >= cutoff:
            # Delete the file
            log.info('Deleting aged backup - %s', backup)
            shutil.rmtree(backup)

def create_tarfile(tar_path: Path, start_dir: Path) -> None:
    """Recursively tars up start_dir and adds all the files in it to the tarball that will be created at tar_path.

    Note that you can simply add the main directory to the tarball and it will handle recursively adding all the files
    under it. However, if adding any single file fails that the entire tarball creation fails and we don't want that.
    For example, there are lost+found directories owned by root that we can't read, a user might manually create some
    files with bad permissions, etc. so we want to log any files we skip but we still want to back up what we can. We
    therefore manually add each file in a try/catch block.
    """
    tar = tarfile.open(tar_path, mode='w:gz')
    to_add = [start_dir]
    while len(to_add) > 0:
        cur_dir = to_add.pop()
        try:
            for file_or_dir in cur_dir.iterdir():
                try:
                    if file_or_dir.is_dir():
                        to_add.append(file_or_dir)
                    else:
                        tar.add(str(file_or_dir))
                except Exception as e:
                    log.warning('Error handling file or directory %s: %s. It will not be saved in the backup.',
                                file_or_dir, e)
        except Exception as e:
            log.warning('Error handling directory %s: %s. It will not be saved in the backup.', cur_dir, e)
    tar.close()


def hardlink_files(src_dir: Path, dest_dir: Path) -> None:
    """Create dest_dir and then hard link all of the files in src_dir into dest_dir."""
    dest_dir.mkdir(parents=True)
    for file in src_dir.iterdir():
        if file.is_dir():
            log.warning('Found unexpected directory: %s', file)
        else:
            os.link(file, dest_dir / file.name)

def dump_db(db_host: str, db_user: str, db_pass: str, dest: Path) -> None:
    """Dump all databases on db_host to file dest."""
    assert dest.suffix == '.gz'
    with open(dest.parent / dest.stem, 'wb') as uncompressed_out:
        subprocess.check_call(
            ['mysqldump', '-h', db_host, '-u', db_user, '--password=' + db_pass, '--all-databases'],
            stdout = uncompressed_out)
        subprocess.check_call(['gzip', dest.parent / dest.stem])

def main():
    """Wakes up every day and makes a backup in the short-term directory. 
    Deletes copies that are older than 7 days old. In the long-term directory, 
    maintains a copy that is between 0 and 30 days old, and a copy that is 
    between 30 and 60s days old.
    The numbers stated above are examples, and are settable by editing the 
    constants above. 
    """
    args = parse_args()
    SHORT_DIR.mkdir(parents=True, exist_ok=True)
    LONG_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        now = datetime.now()
        timestamp = now.strftime(DATE_TIME_FORMAT)

        # Archive the directory
        log.info('Archiving %s', timestamp)
        backup_dir = SHORT_DIR / timestamp
        backup_dir.mkdir(parents=True)
        log.info('Backing up files')
        create_tarfile(backup_dir / 'files.tar.gz', SRC_DIR)
        log.info('Dumping the database')
        dump_db(args.db_host, args.db_user, args.db_pass, backup_dir / 'dbdump.sql.gz')
        log.info('Archive at %s complete', timestamp)

        # Delete the archves that are too old
        delete_too_old(SHORT_DIR, now, args.short_keep)

        # Archive long-term copy if necessary
        # If there are no long-term copies
        if len(os.listdir(LONG_DIR)) == 0:
            # Make hard links of the files to save disk space
            long_backup_dir = LONG_DIR / backup_dir.name
            hardlink_files(backup_dir, long_backup_dir)
        else:
            long_backups = get_backup_list(LONG_DIR)
            # Update long-term archive if newest one is older than long duration
            if dirname2age(now, long_backups[-1].name) >= args.long_freq:
                log.info('Hard linking %s to longs', backup_dir)
                long_backup_dir = LONG_DIR / backup_dir.name
                hardlink_files(backup_dir, long_backup_dir)
                delete_too_old(LONG_DIR, now, args.long_keep)

        log.info('Sleeping for %s == %s seconds', args.backup_freq, args.backup_freq.total_seconds())
        time.sleep(args.backup_freq.total_seconds())

if __name__ == '__main__':
    main()
