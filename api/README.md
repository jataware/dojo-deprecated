# DMC API

This is a FastAPI webapp that provides an interface to the Domain Model Controller execution engine. It is a re-implementation of the SuperMaaS API.

## Installation

`pip install -r requirements.txt`

## Run the webapp


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

## Usage

The only 3 endpoints currently working are the `/models` endpoints. You can "create" the MaxHop model as an example with:

```
curl -X POST -H "Content-Type: application/json" -d @examples/maxhop.json localhost:8000/models
```

You can then search with:

```
curl -XGET 'http://localhost:8000/models?query=locusts'
```

Note that the `query` parameter can be any valid Lucene Syntax query against the Elasticsearch schema, but it must be url encoded. For example you may query for `(locusts) AND (jataware)` with:

```
curl -XGET 'http://localhost:8000/models?query=%28locusts%29%20AND%20%28jataware%29'
```

You can query for things like `maintainer.name: kyle` or `created_at:<=2021-03-30`

## TODO

* The schema does not inclued `created_at`, but this is added upon indexing to ES. This seems suboptimal
* The schema for `ModelOutputFile.transform` is just an arbitrary dictionary. This ultimately needs to be further refined into a schema that can map to the data annotation UI
* Currently we allow for Jinja templating in the output file name, but if the output file names rely on timestamps or are somehow random, this will be a major problem.
