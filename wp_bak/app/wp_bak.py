#!/usr/bin/env python3
# Todo:
# -- use timestamp in name
# -- add logging
# -- delete older than X
# -- logic for keeping a single old one
# Docker:
# docker build -t colindavey/wp_bak:stub .
# docker run -v `pwd`/src:/home/mvp/app/src -v `pwd`/dst:/home/mvp/app/dst -t colindavey/wp_bak:stub

from datetime import datetime
from fnmatch import fnmatch
import logging
import os
import sys
import tarfile
import time

SRC_DIR='src/'
DST_DIR='dst/'

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY

DATE_TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

# Number of seconds between backups
PERIOD = 1
PERIOD_TO_KEEP = 10

i = 0
num_reps = 30

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
log = logging.getLogger(__name__)

while True:
    time.sleep(PERIOD)
    now = datetime.now()
    timestamp = now.strftime(DATE_TIME_FORMAT)

    # Archive the directory
    log.info('Archiving %s', timestamp)
    tar = tarfile.open(DST_DIR+'archive'+timestamp+'.tar.gz', mode='w:gz')
    tar.add(SRC_DIR)
    tar.close

    archives = list(filter(lambda x: fnmatch(x, 'archive*.tar.gz'), os.listdir(DST_DIR)))
    for archive in archives:
        # Get string representation of archive date
        archive_date = archive.replace('archive', '').replace('.tar.gz', '')
        print(datetime.strptime(archive_date, DATE_TIME_FORMAT))
        # Get age from archive-date string
        archive_age = now - datetime.strptime(archive_date, DATE_TIME_FORMAT)
        archive_age = (archive_age.days * DAY) + archive_age.seconds
        if archive_age > PERIOD_TO_KEEP:
            os.remove(DST_DIR + archive)

    i = i + 1
    if(i > num_reps):
        break
