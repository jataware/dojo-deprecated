#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = 'http://localhost:8000'
headers = {'Content-Type': 'application/json'}


#### Create Model
payload = open('maxhop.json').read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)


#### Add Directive
directive = {
    "id": "maxhop-directive-1",
    "model_id": "maxhop-v0.2",
    "command": "--country={{ country }} --annualPrecipIncrease={{ annualPrecipIncrease }} --meanTempIncrease=-{{ meanTempIncrease }} --format=GTiff",
    "output_directory": "/usr/local/src/myscripts/output"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
resp.text


#### Add OutputFile
mapper = json.loads(open('mapper.json').read())
outputfile = {
    "id": "maxhop-outputfile-1",
    "model_id": "maxhop-v0.2",
    "name": "Hopper Presence Prediction",
    "file_type": "geotiff",
    "path": "maxent_Ethiopia_precipChange={{ annualPrecipIncrease }}tempChange=-{{ meanTempIncrease }}.tif",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
resp.text