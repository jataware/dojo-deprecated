#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("conflict.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/9e896392-2639-4df6-b4b4-e1b1d4cf46ae/7c4c890db081265c77b8ede2a4bbefdc.template.txt",
    "model_id": "9e896392-2639-4df6-b4b4-e1b1d4cf46ae",
    "command": '/bin/bash -c "sudo chmod -R 777 output; set -a; source .env; luigi --module models.conflict_model.tasks models.conflict_model.tasks.Predict --peaceful-days {{ peaceful_days }} --youth-bulge {{ youth_bulge_percentage_change }} --drought-index {{ drought_index_evaporative_stress_index }} --local-scheduler"'
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add OutputFile 1
mapper = json.loads(open("conflict_mapper.json").read())
# TODO: fix the path with correct one
outputfile = {
    "id": "conflict-outputfile-1",
    "model_id": "9e896392-2639-4df6-b4b4-e1b1d4cf46ae",
    "name": "conflict onset",
    "file_type": "csv",
    "output_directory": "/usr/src/app/output",
    "path": "final_targets/hoa_conflict_forecast_*.csv",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)