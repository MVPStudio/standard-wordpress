FROM mvpstudio/python:v4 as base

# Install mariadb-client to get mysqldump cli
RUN apt-get update && apt-get install -y mariadb-client

USER mvp
COPY app /home/mvp/app
WORKDIR /home/mvp/app

ENTRYPOINT ["/usr/bin/python3", "wp_bak.py"]
