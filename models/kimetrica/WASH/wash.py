#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("wash.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
  "id": "dojo/shorthand_templates/efde67cb-d6f3-4bd4-aed0-25b9748534fd/9240514bd3360e84cc842c773e59983a.template.txt",
  "model_id": "efde67cb-d6f3-4bd4-aed0-25b9748534fd",
  "command": '/bin/bash -c "sudo chmod -R 777 output; set -a; source .env; luigi --module models.water_sanitation_model.tasks models.water_sanitation_model.tasks.PredictUnimprovedSanitation --country-level \'{{ country }}\' --time {{ date_range }} --travel-time-percent-change {{ travel_time_percent_change }} --aridity-index-percent-change {{ aridity_index_percent_change }} --night-light-percent-change 0 --local-scheduler"',
  "output_directory": "/results"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add OutputFile 1
mapper = json.loads(open("unimproved_sanitation_mapper.json").read())
outputfile = {
    "id": "wash-outputfile-1",
    "model_id": "efde67cb-d6f3-4bd4-aed0-25b9748534fd",
    "name": "unimproved sanitation",
    "file_type": "netcdf",
    "output_directory": "/usr/src/app/output",
    "path": "final_targets/water_sanitation_model/unimproved_sanitation_Ethiopia_*.nc",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)