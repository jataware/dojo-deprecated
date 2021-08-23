#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}


#### Create Model
payload = open("maxhop.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)


#### Add Directive
directive = {
    "id": "maxhop-directive-1",
    "model_id": "maxhop-v0.2",
    "command": "--country={{ country }} --annualPrecipIncrease={{ annualPrecipIncrease }} --meanTempIncrease={{ meanTempIncrease }} --format=GTiff",
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)


#### Add OutputFile
mapper = json.loads(open("mapper.json").read())
outputfile = {
    "id": "maxhop-outputfile-1",
    "model_id": "maxhop-v0.2",
    "name": "Hopper Presence Prediction",
    "file_type": "geotiff",
    "output_directory": "/usr/local/src/myscripts/output",
    "path": "maxent_*_precipChange=*tempChange=*.tif",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)
