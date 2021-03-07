#!/usr/bin/env python3
# Docker:
# docker build -t colindavey/wp_bak:alpha .
# docker run -v `pwd`/src:/home/mvp/app/src -v `pwd`/dst:/home/mvp/app/dst -t colindavey/wp_bak:alpha

from datetime import datetime
from fnmatch import fnmatch
import logging
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time

#############################
# CONSTANTS
#############################

SRC_DIR=Path('src')
DST_DIR=Path('dst')
SHORT_DIR=DST_DIR.joinpath('shorts')
LONG_DIR=DST_DIR.joinpath('longs')

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY

DATE_TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

# Duration between backups in seconds
# Actual value
# SHORT_DURATION = DAY
# Value for testing
SHORT_DURATION = 1
# Delete everything in the shorts folder older than this
SHORT_DURATION_TO_KEEP = 7 * SHORT_DURATION

LONG_DURATION = 30 * SHORT_DURATION
# Delete everything in the longs folder older than this
LONG_DURATION_TO_KEEP = 2 * LONG_DURATION

# Set to a value for testing
# NUM_REPS = None
NUM_REPS = 100

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
log = logging.getLogger(__name__)

#############################
# FUNCTIONS
#############################

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
    date = filename.replace('archive', '').replace('.tar.gz', '')
    # Get age from archive-date string
    age = now - datetime.strptime(date, DATE_TIME_FORMAT)
    return (age.days * DAY) + age.seconds

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

    cutoff : integer, number of seconds
        The age, older than which, we delete the file.
    """
    archives = get_archive_list(dir)
    for archive in archives:
        if filename2age(now, archive) >= cutoff:
            # Delete the file
            dir.joinpath(archive).unlink()

def main():
    """Wakes up every day and makes a backup in the short-term directory. 
    Deletes copies that are older than 7 days old. In the long-term directory, 
    maintains a copy that is between 0 and 30 days old, and a copy that is 
    between 30 and 60s days old.
    The numbers stated above are examples, and are settable by editing the 
    constants above. 
    """
    SHORT_DIR.mkdir(parents=True, exist_ok=True)
    LONG_DIR.mkdir(parents=True, exist_ok=True)
    rep = 0

    while True:
        time.sleep(SHORT_DURATION)
        now = datetime.now()
        timestamp = now.strftime(DATE_TIME_FORMAT)

        # Archive the directory
        log.info('Archiving %s', timestamp)
        tar_filename = SHORT_DIR.joinpath('archive'+timestamp+'.tar.gz')
        tar = tarfile.open(tar_filename, mode='w:gz')
        tar.add(SRC_DIR)
        tar.close

        # Delete the archves that are too old
        delete_too_old(SHORT_DIR, now, SHORT_DURATION_TO_KEEP)

        # Archive long-term copy if necessary
        # If there are no long-term copies
        if len(os.listdir(LONG_DIR)) == 0:
            shutil.copy(tar_filename, LONG_DIR)
        else:
            long_archives = get_archive_list(LONG_DIR)
            # Update long-term archive if newest one is gt duration
            if filename2age(now, long_archives[0]) >= LONG_DURATION:
                shutil.copy(tar_filename, LONG_DIR)
                delete_too_old(LONG_DIR, now, LONG_DURATION_TO_KEEP)

        if NUM_REPS is not None:
            rep = rep + 1
            print('rep:', rep)
            if(rep > NUM_REPS):
                break

if __name__ == '__main__':
    main()
