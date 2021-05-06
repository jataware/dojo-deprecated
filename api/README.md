# Dojo API

This is a FastAPI webapp that provides an interface to the Domain Model Controller execution engine.

## Installation

`pip install -r requirements.txt`

## Run the webapp

First you will need to determine your local machine IPv4

For OSX
```
ipconfig getifaddr en0
```
For Linux
```
hostname -i
```

Put this into `config.ini` for the `DMC URL` and within the `DOJO URL` (keep the `http://` and `:8000`, just swap the IP).

To run this API, along with Elasticsearch and Kibana, run:


```
docker-compose up --build -d

```

This will build the API container and run the server on `http://localhost:8000/`

## Running the webapp in development

To run the API for development purposes use:

```
docker-compose -f docker-compose-dev.yaml up --build -d
```

This will turn on the API, Elasticsearch and Kibana, but the API will be in `reload` mode and any changes made to the local repository will be reflected in the container to facilitate development.

## Setup

First, you should create the example model (MaxHop) with:

```
cd examples
python3 Examples.py
```

Then you should create the `runs` index mapping for Elasticsearch with:

```
cd es-mappings
python3 CreateMappings.py
```