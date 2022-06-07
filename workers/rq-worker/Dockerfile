FROM --platform=linux/amd64 jataware/mixmasta:latest

RUN pip install --upgrade pip

COPY ./tasks/requirements.txt /tasks/requirements.txt
WORKDIR /tasks
RUN pip install -r requirements.txt
COPY ./tasks /tasks


ENV PYTHONPATH "${PYTHONPATH}:/api"
