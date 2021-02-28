#!/usr/bin/env python3
# Todo:
# -- use timestamp in name
# -- delete older than X
# -- logic for keeping a single old one
# -- add logging
# Docker:
# docker build -t colindavey/wp_bak:stub .
# docker run -v `pwd`/src:/home/mvp/app/src -v `pwd`/dst:/home/mvp/app/dst -t colindavey/wp_bak:stub

from datetime import datetime
# import logging
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
# NUM_TO_KEEP = 4

i = 0
num_reps = 3

while True:
    time.sleep(PERIOD)

    tar = tarfile.open(DST_DIR+'archive'+datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+'tar.gz', mode='w:gz')
    tar.add(SRC_DIR)
    tar.close

    print(i)
    i = i + 1
    if(i > num_reps):
        break
