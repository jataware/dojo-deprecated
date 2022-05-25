FROM --platform=linux/amd64 python:3.10.0

RUN pip install --upgrade pip

COPY ./api /api
WORKDIR /api

RUN pip install -r requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/api"