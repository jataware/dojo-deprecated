FROM python:3.10-slim-buster

COPY scripts/ /home/apps/scripts/

RUN useradd --user-group --create-home apps && \
    usermod -s /bin/bash apps && \
    chown -v -R apps:apps /home/apps

USER apps
WORKDIR /home/apps/scripts

RUN pip install --upgrade pip --user && \
    pip install --user -r requirements.txt

ENTRYPOINT ["python"]
CMD []