FROM mvpstudio/python:v4 as base

# RUN pip3 install requests
# RUN pip3 install requests
# RUN pip3 install openpyxl
# RUN pip3 install Flask

# EXPOSE 80
# EXPOSE 443
# EXPOSE 5000

USER mvp
COPY app /home/mvp/app
WORKDIR /home/mvp/app

ENTRYPOINT ./wp_bak.py
