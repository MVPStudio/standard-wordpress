FROM mvpstudio/python:v4 as base

# Install mariadb-client to get mysqldump cli. The mkdir and chmod here
# are only necessary for the docker-compose stuff to work. Otherwise the
# mounted /dst volume is owned by root and not writable.
RUN apt-get update && apt-get install -y mariadb-client && \
   mkdir /dst && chmod a+rwx /dst

USER mvp
COPY app /home/mvp/app
WORKDIR /home/mvp/app

ENTRYPOINT ["/usr/bin/python3", "wp_bak.py"]
