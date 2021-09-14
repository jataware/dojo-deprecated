#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("apsim.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/deeaae7d-2820-4019-b7af-0e9ffd4455bb/e430d780b828ca3754ff16af3a4d6e40.template.txt",
    "model_id": "deeaae7d-2820-4019-b7af-0e9ffd4455bb",
    "command": "curl -o results.csv https://worldmodel.csiro.au/grange?country={{ country }}\\&weather=forecast\\&aggregation=annual\\&year={{ year }}",
    "output_directory": "/results"
  }
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)


#### Add OutputFile
outputfiles = json.loads(open("apsim_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)

#### Add accessories
# accessories = json.loads(open("apsim_accessories.json").read())
# resp = requests.put(f"{url}/dojo/accessories", json=accessories)
# print(resp.text)

