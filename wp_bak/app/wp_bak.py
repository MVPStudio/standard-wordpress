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
import logging
import sys
import tarfile
import time

SRC_DIR='src/'
DST_DIR='dst/'

MINUTE=60
HOUR=60*MINUTE
DAY=24*HOUR
WEEK=7*DAY

# Number of seconds between backups
PERIOD = 2
PERIOD_TO_KEEP = 4

i = 0
num_reps = 3

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
log = logging.getLogger(__name__)

while True:
    time.sleep(PERIOD)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    tar = tarfile.open(DST_DIR+'archive'+timestamp+'tar.gz', mode='w:gz')
    tar.add(SRC_DIR)
    tar.close
    log.info('Archiving %s', timestamp)

    i = i + 1
    if(i > num_reps):
        break
