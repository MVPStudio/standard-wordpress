FROM mvpstudio/python:v4 as base

USER mvp
COPY app /home/mvp/app
WORKDIR /home/mvp/app

ENTRYPOINT ["/usr/bin/python3", "wp_bak.py"]
