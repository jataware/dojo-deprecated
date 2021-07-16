FROM python:3.8

WORKDIR /

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY / .

ENTRYPOINT ["python3","./trends.py"]
