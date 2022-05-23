FROM --platform=linux/amd64 python:3.10.0

RUN pip install --upgrade pip

COPY ./api /api
WORKDIR /api

RUN pip install rq fastapi elasticsearch==7.12.0 requests

ENV PYTHONPATH "${PYTHONPATH}:/api"