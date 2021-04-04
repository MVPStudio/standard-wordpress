#!/usr/bin/env python3
# Docker:
# docker build -t mvpstudio/wordpress-backup:v0001 .
# docker run -v `pwd`/src:/src -v `pwd`/dst:/dst -t mvpstudio/wordpress-backup:v0001

import argparse
from datetime import datetime, timedelta
from fnmatch import fnmatch
import re
import logging
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time
from typing import Optional

#############################
# CONSTANTS
#############################

SRC_DIR=Path('/src')
DST_DIR=Path('/dst')
SHORT_DIR=DST_DIR.joinpath('shorts')
LONG_DIR=DST_DIR.joinpath('longs')

DATE_TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
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

    return parsed


def filename2age(now, filename):
    """Calculcates the age of a file, in seconds from the files name.

    Parameters
    ----------
    now : datetime object
        The time to use as "now" for calculating item's age.

    filename : string, path of file
        The name of file to calculate age of.
    """
    # Get string representation of archive date
    date_str = filename.replace('archive', '').replace('.tar.gz', '')
    # Get age from archive-date string
    return now - datetime.strptime(date_str, DATE_TIME_FORMAT)

def get_archive_list(dir):
    """Returns a sorted list of archive files from the specified directory.

    Parameters
    ----------
    dir : string, name of directory
        The directory to list.
    """
    return sorted(list(filter(lambda x: fnmatch(x, 'archive*.tar.gz'), os.listdir(dir))), reverse=True)

def delete_too_old(dir, now, cutoff):
    """Deletes everything in the specified directory that is older than the cutoff.

    Parameters
    ----------
    dir : string, name of directory
        The directory to prune.

    now : datetime object
        The time to use as "now" for calculating item's age.

    cutoff : timedelta object
        The age, older than which, we delete the file.
    """
    archives = get_archive_list(dir)
    for archive in archives:
        if filename2age(now, archive) >= cutoff:
            # Delete the file
            log.info('Deleting aged archive - %s', archive)
            dir.joinpath(archive).unlink()

def filter_lost_and_found(ti: tarfile.TarInfo) -> Optional[tarfile.TarInfo]:
    """Filter out lost+found directories.

    Our storage layer creates lost+found directories but these are owned by root and not accessible to the backup so we
    have to filter them out of the tarfile. This is a function that can be passed to the filter argument of tarfile.add
    to do that.
    """
    if ti.path is not None:
        as_path = Path(ti.path)
        if as_path.name == 'lost+found':
            log.info('Dropping lost+found file/dir: %s', as_path)
            return None
    return ti

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
        tar_filename = SHORT_DIR.joinpath('archive'+timestamp+'.tar.gz')
        tar = tarfile.open(tar_filename, mode='w:gz')
        # Our storage layer creates lost+found directories that we don't have permissions to and that would cause
        # the backup to fail so we filter those out.
        tar.add(SRC_DIR, filter=filter_lost_and_found)
        tar.close()
        log.info('Archive at %s complete', timestamp)

        # Delete the archves that are too old
        delete_too_old(SHORT_DIR, now, args.short_keep)

        # Archive long-term copy if necessary
        # If there are no long-term copies
        if len(os.listdir(LONG_DIR)) == 0:
            shutil.copy(tar_filename, LONG_DIR)
        else:
            long_archives = get_archive_list(LONG_DIR)
            # Update long-term archive if newest one is older than long duration
            if filename2age(now, long_archives[0]) >= args.long_freq:
                shutil.copy(tar_filename, LONG_DIR)
                delete_too_old(LONG_DIR, now, args.long_keep)

        time.sleep(args.backup_freq.total_seconds())

if __name__ == '__main__':
    main()