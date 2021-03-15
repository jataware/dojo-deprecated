FROM python:3.9.2


RUN pip install --upgrade pip

COPY . /dmc-api
WORKDIR /dmc-api

RUN pip install -r requirements.txt

CMD ["uvicorn", "server:api", "--reload"]