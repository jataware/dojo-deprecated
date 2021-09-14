#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("topoflow.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
  "id": "dojo/shorthand_templates/09956c86-79c7-47f7-80d2-25b72d79948a/66990cd026d3b6262281772734272426.template.txt",
  "model_id": "2ddd2cbe-364b-4520-a28e-a5691227db39",
  "command": "/bin/bash -c \"mint2dojo topoflow --start_date {{ start_date }} --end_date {{ end_date }} --basin {{ basin }}; bash file-mover.sh\"",
  "output_directory": "/results"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)


#### Add OutputFile
outputfiles = json.loads(open("topoflow_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)

#### Add accessories
accessories = json.loads(open("topoflow_accessories.json").read())
resp = requests.put(f"{url}/dojo/accessories", json=accessories)
print(resp.text)

