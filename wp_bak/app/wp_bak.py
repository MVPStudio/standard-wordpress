#!/usr/bin/env python3
import tarfile
import time

SRC_DIR='src/'
DST_DIR='dst/'

MINUTE=60
HOUR=60*MINUTE
DAY=24*HOUR
WEEK=7*DAY

# docker build -t colindavey/wp_bak:stub .
# docker run -v `pwd`/src:/home/mvp/app/src -v `pwd`/dst:/home/mvp/app/dst -t colindavey/wp_bak:stub

# Number of seconds between backups
PERIOD = 2

i = 0
num_reps = 3

while True:
    time.sleep(PERIOD)

    tar = tarfile.open(DST_DIR+'archive'+str(i)+'tar.gz', mode='w:gz')
    tar.add(DST_DIR)
    tar.close

    print(i)
    i = i + 1
    if(i > num_reps):
        break
