#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("malnutrition.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/425f58a4-bbba-44d3-83f3-aba353fc7c64/73d98cd3ecf0a0a0013780f369b3d297.template.txt",
    "model_id": "425f58a4-bbba-44d3-83f3-aba353fc7c64",
    "command": '/bin/bash -c "sudo chmod -R 777 output; set -a; source .env; luigi --module models.malnutrition_model.tasks models.malnutrition_model.tasks.MalnutInference --time {{ time_range }} --rainfall-scenario-time {{ rainfall_scenario_time_range }} --country-level \'{{ country }}\' --rainfall-scenario {{ rainfall_scenario }} --local-scheduler"'
  }
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add OutputFile 1
mapper = json.loads(open("malnutrition_mapper.json").read())
outputfile = {
    "id": "malnutrition-outputfile-1",
    "model_id": "425f58a4-bbba-44d3-83f3-aba353fc7c64",
    "name": "malnutrition",
    "file_type": "csv",
    "output_directory": "/usr/src/app/output",
    "path": "final_targets/maln_inference_*.csv",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)