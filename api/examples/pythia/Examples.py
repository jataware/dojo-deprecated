#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = 'http://localhost:8000'
headers = {'Content-Type': 'application/json'}


#### Create Model
payload = open('pythia_short.json').read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)
#
# #### Add Directive
directive = {
    "id": "pythia-directive-1",
    "model_id": "dssat_pythia-v0.1_short",
    "command": "--all /userdata/et_docker.json",
    "output_directory": "/userdata/out/eth_docker/test/"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)
#
#
# #### Add OutputFile
mapper = json.loads(open('mapper.json').read())
outputfile = {
    "id": "pythia-outputfile-1",
    "model_id": "dssat_pythia-v0.1_short",
    "name": "DSSAT-PYTHIA",
    "file_type": "csv",
    "path": "pp.csv",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)
#

# ## Add config
# copy data from config_pythia.json into the dojo api create config endpoint at
# http://localhost:8000/#/Dojo/create_configs_dojo_config_post