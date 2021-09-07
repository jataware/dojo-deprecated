#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}


#### Create Model
payload = open("dummy_model.json").read()
print(payload)
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)
# #
# #### Add Directive
directive = {
    "id": "dummy-directive-1",
    "model_id": "dummy-model-v0.1",
    "command": "python /model/main.py --temp={{temp}}",
    "output_directory": "/model/output",
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)
#
#
# #### Add OutputFile
mapper = json.loads(open("mapper.json").read())
outputfile = {
    "id": "dummy-outputfile-1",
    "model_id": "dummy-model-v0.1",
    "output_directory": "/model/output",
    "path": "output.csv",
    "name": "dummy-model",
    "file_type": "csv",
    "output_directory": "/model/output",
    "path": "output_*_*.csv",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)

#### Add config
config = json.loads(open("config_dummy_model.json").read())
resp = requests.post(f"{url}/dojo/config", json=config)
print(resp.text)

#### Add accessories
accessories = json.loads(open("dummy_accessories.json").read())
resp = requests.put(f"{url}/dojo/accessories", json=accessories)
print(resp.text)
