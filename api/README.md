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

Put this into `.env` for the `DMC URL` and within the `DOJO URL` (keep the `http://` and `:8000`, just swap the IP). You will also need to specify the path to the DMC directory.

> Note: you can override values in the `.env` file by setting them in your environment directly. For example `export ELASTICSEARCH_PORT=9200` will take precedence over what is specified in the `.env` file.

To run this API, along with Elasticsearch and Kibana, run:

```
docker-compose up --build -d

```

This will build the API container and run the server on `http://localhost:8000/`

## Running the webapp in development

To run the API for development purposes use:

```
docker-compose -f docker-compose-dev.yaml up -d
```

This will turn on the API, Elasticsearch and Kibana, but the API will be in `reload` mode and any changes made to the local repository will be reflected in the container to facilitate development.

You should also ensure that `CAUSEMOS_DEBUG` in `.env` is set to `true` as this will bypass notifying Uncharted that indicators were created. In production, this should be set to `false` so that Uncharted gets notified whenever a new indicator is created.

## Setup

There are two example models to run; from the top of this repository run:

MaxHop Example:

```
cd models/maxhop
python3 maxhop.py
```

Pythia Example:

```
cd examples/pythia
python3 pythia.py
```


Then you should create the `runs` index mapping for Elasticsearch with:

```
cd ../api/es-mappings
python3 CreateMappings.py
```

## Running the examples

For each example (`MaxHop` and `pythia`) there is a `run_<model>.json` file. Copy and paste the contents into Dojo's create `run/` endpoint (http://localhost:8000/#/Runs/create_run_runs_post) then navigate to airflow (http://localhost:8080) to monitor model execution.

## Logging

To set the log level, change the level for FastAPI in `logging.yaml`. 

## Schema Validation

This step only needs to be done after an Uncharted schema change. While the steps below will auto-build the pydantic schema files in the `validation/` folder, you may need to update the .py files in the `src/` directory with any schema class name changes.

To retrieve and build pydantic .py files from the lastest schema jsons from Uncharted run:

```
chmod 755 json_to_pydantic.sh
./json_to_pydantic.sh
``` 
This shell script clones the Uncharted Schema repo, builds the the pydantic schemas via `datamodel-codegen` (as described [here](https://pydantic-docs.helpmanual.io/datamodel_code_generator/)), then deletes the Uncharted Repo.  Note that an external `$ref` under `model_id` is removed from `model-run.schema.json` and proper conversion to pydantic schema should be verified.