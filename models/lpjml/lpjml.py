#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("lpjml.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
  "id": "dojo/shorthand_templates/9f407b82-d2d2-4c38-a2c3-ae1bb483f476/e2a480f0d4b7bc7491c26a35a2a1f652.template.txt",
  "model_id": "9f407b82-d2d2-4c38-a2c3-ae1bb483f476",
  "command": "./download_forecast.sh -fertilizer_scenario {{ fertilizerscenario }} -sowing_scenario {{ sowingscenario }} -weather_year {{ weatheryear }}",
  "output_directory": "/results"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)


#### Add OutputFile
outputfiles = json.loads(open("lpjml_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)
