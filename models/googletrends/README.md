# Google Trends Model

Details on the Google Trends Model can be found [here](https://github.com/jataware/open-indicators/tree/master/google-trends).

## Running Google Trends in Dojo

Update the following:

- `api/src/settings.py`: change REDIS_PORT to 6380
- `api/docker-compose.yaml`: change line 47 to 6380:6379
- Delete Elasticsearch volumes associated with Dojo API (save anything you may need/want)
- Run:


      cd api/es-mappings
      python3 CreateMappings.py

- Then, create the google_trends model with:

      cd ~models/googletrends
      python3 google_trends.py

- Go to: `http://localhost:8000/#/Runs/create_run_runs_post` to submit a model run:
   - `google_trends_run.json` is an example; you may use it as is or change the desired search term and geographic area(s) reflected in the `parameters` dictionary. Update the `model_id` for subsequent runs.

- Inspect the DAG at `http://localhost:8080/` to monitor model run progress.
