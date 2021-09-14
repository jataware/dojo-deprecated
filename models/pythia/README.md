# pythia model
This folder contains the files required to run [pythia](https://github.com/DSSAT/pythia) in Dojo:

## File Descriptions:

- `Dockerfile`: builds Docker image to run `pythia`. Assumes `claudine` and `sshd` directories from Clouseau are in the same directory.

- `config_pythia.json`: Assigns location of the dehydrated config file on S3. A dehydrated config is a shell that allows the user to "hydrate" the config file on the fly with user-specified model parameter values.

- `et_docker.json`: For Reference Only; this is a copy of the dehydrated configuration for ease of inspection. The dehydrated config used in Dojo is located at: https://jataware-world-modelers.s3.amazonaws.com/dojo/configs/et_docker.json

- `mapper.json`: Created with SpaceTag, this file facilitates geocoding and causemosification of model output files via mixmasta.

- `pythia.json`: model, parameter, and output metadata that aligns with Uncharted's schema requirements.

- `run_pythia.json`: For a specific model run, this file "hydrates" the dehydrated `config_pythia.json` with the user-desired values.

- `pythia.py`: Loads the model for execution in Dojo. Note that:
   - The model payload (`pythia.json`) must match the json file you have in this directory
   - The config payload (`config_pythia.json`) must match the json file you have in this directory
   - To properly load the model via this script, the `model-id` and `model_name` must be consistent across all files: `config_pythia.json`, `pythia.json`, `TEST_RUN.json`, and `Examples.py`.

## Running pythia in Dojo

- Follow the [API](https://github.com/jataware/dojo/tree/master/api) and [DMC](https://github.com/jataware/dojo/tree/master/dmc) set-up instructions 
- Load the example pythia model with:

	```
	cd ~examples/pythia
	python3 pythia.py
	```
	Running pythia.py creates the model directive, outputfile, and config ElasticSearch entries used by Dojo.
	
- Update `TEST_RUN.json` with desired model parameter values

- Copy and paste `run_pythia.json` into [/runs](http://localhost:8000/#/Runs/create_run_runs_post) and execute model run.