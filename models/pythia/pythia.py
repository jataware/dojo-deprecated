#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("pythia.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "pythia-directive-1",
    "model_id": "dssat_pythia-v0.1",
    "command": "--all /userdata/et_docker.json",
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add OutputFile
mapper = json.loads(open("mapper.json").read())
outputfile = {
    "id": "pythia-outputfile-1",
    "model_id": "dssat_pythia-v0.1",
    "name": "DSSAT-PYTHIA",
    "file_type": "csv",
    "output_directory": "/userdata/out/eth_docker/test/",    
    "path": "pp.csv",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)

##### Add config
config = json.loads(open("config_pythia.json").read())
resp = requests.post(f"{url}/dojo/config", json=config)
print(resp.text)
