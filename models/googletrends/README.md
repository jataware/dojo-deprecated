# Google Trends Model

Details on the Google Trends Model can be found [here](https://github.com/jataware/open-indicators/tree/master/google-trends).

## Running Google Trends in Dojo

Follow all instructions for running Dojo and DMC. Prior to running Dojo, there are two changes that must occur manually to avoid conflicting Redis port usage.

- api/src/settings.py: change REDIS_PORT to 6380
- api/docker-compose.yaml: change line 47 to 6380:6379
- Delete any lingering or old Elasticsearch volumes associated with Dojo API (unless they have something you wish to save--in that case back them up).
Then run Dojo/DMC as you normally would.

Next run:

'''
cd api/es-mappings
python3 CreateMappings.py
'''

Then,

'''
cd ~models/googletrends
python3 google_trends.py
'''

Submit a model run `google_trends_run.json` with desired search term and geographic area(s) reflected in the `parameters` dictionary.