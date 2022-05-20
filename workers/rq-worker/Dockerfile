FROM --platform=linux/amd64 python:3.10.0

RUN pip install --upgrade pip

RUN pip install rq

CMD ["rq", "worker", "--url", "redis://redis1:6379", "high", "default", "low"]