# Kimetrica Models

The Kimetrica models can be run from a single container. To facilitate model registration with their container, we have a fork of their Dockerfile in `Dockerfile` here. This not only builds their container, but injects it with Clouseau dependencies so that it will work in the Phantom UI.

To build this container you must clone the [Kimetrica repo](https://gitlab.com/kimetrica/darpa/darpa/-/tree/master/) and replace [`kimetrica-darpa-models/Dockerfile`](https://gitlab.com/kimetrica/darpa/darpa/-/blob/master/docker/kimetrica-darpa-models/Dockerfile) with the `Dockerfile` here. Additionally, you must ensure that you have have [`claudine`](https://github.com/jataware/clouseau/tree/master/claudine) and [`sshd`](https://github.com/jataware/clouseau/tree/master/sshd) directories in the Kimetrica root directory.

You also need to have a correct `.env` file at the top level of the Kimetrica repo which contains CKAN and other credentials. Kimetrica has provided this and it is baked into the pre-built version of this container.

Currently this docker image is available on Dockerhub at `jataware/clouseau:claudine_ki_models` and can be fetched with `docker pull jataware/clouseau:claudine_ki_models`.

## Running a Kimetrica model

The Kimetrica models can be executed with more or less the same kind of `luigi` command. For example, the following will run the malnutrition model:

```
docker run -v $PWD/output:/usr/src/output jataware/kimetrica-darpa-models /bin/bash -c "set -a; source .env; luigi --module models.malnutrition_model.tasks models.malnutrition_model.tasks.MalnutritionInferenceGeoJSON --time 2015-01-01-2015-06-01 --rainfall-scenario-time 2015-05-01-2015-05-10 --country-level Ethiopia --geography /usr/src/app/models/geography/boundaries/ethiopia_2d.geojson --rainfall-scenario-geography /usr/src/app/models/geography/boundaries/ethiopia_2d.geojson --rainfall-scenario high --local-scheduler"
```

> Note: you must run `set -a; source .env` prior to running the `luigi` command to ensure the environment variables are set. These are baked into the container in the `.env` file at `/usr/src/app/.env`.

This will save the model output to `$PWD/output`. Each model output has a different name, and the Kimetrica team will have to indicate the naming convention for each model. They do seem to be appended with some `UUID` which may be potentially problematic.