# DMC API

This is a FastAPI webapp that provides an interface to the Domain Model Controller execution engine. It is a re-implementation of the SuperMaaS API.

## Installation

`pip install -r requirements.txt`

## Run the webapp


To run this API, along with Elasticsearch and Kibana, run:


```
docker-compose up --build -d

```

This will build the API container.

## Running the webapp in development

To run the API for development purposes use:

```
docker-compose -f docker-compose-dev.yaml up --build -d
```

This will turn on the API, Elasticsearch and Kibana, but the API will be in `reload` mode and any changes made to the local repository will be reflected in the container to facilitate development.