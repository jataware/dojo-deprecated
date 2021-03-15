FROM python:3.9.2


RUN pip install --upgrade pip

COPY . /dmc-api
WORKDIR /dmc-api

RUN pip install -r requirements.txt

EXPOSE 80
CMD ["uvicorn", "server:api", "--host", "0.0.0.0", "--port", "80"]