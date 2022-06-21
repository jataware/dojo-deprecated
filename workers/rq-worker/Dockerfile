FROM --platform=linux/amd64 python:3.10.0

RUN apt-get update &&\
    apt-get install -y gdal-bin libgdal-dev

RUN pip install --upgrade pip

COPY ./tasks/requirements.txt /tasks/requirements.txt
WORKDIR /tasks
RUN pip install -r requirements.txt
COPY ./tasks /tasks


ENV PYTHONPATH "${PYTHONPATH}:/api"
