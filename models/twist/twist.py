#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}


#### Create Model
payload = open("twist.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)


#### Add Directive
directive = {
  "id": "dojo/shorthand_templates/40f08e3a-bc03-4416-ab85-120b4bf5a46b/679faac61563c8308423d5084ab27d71.template.txt",
  "model_id": "40f08e3a-bc03-4416-ab85-120b4bf5a46b",
  "command": "./run_TWIST.py --crop {{ crop }} --scenario_type '2021_scenario' --include_prodDecline {{ inclusion_of_production_decline }} --include_exportRestr {{ inclusion_of_export_restriction }} --length_of_scenario {{ length_of_scenario }}",
  "output_directory": "/results"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)


##### Add config
config =   {
    "id": "dojo/shorthand_templates/40f08e3a-bc03-4416-ab85-120b4bf5a46b/26e184b8b8a861c26e703e4bdfaeef0a.template.txt",
    "model_id": "40f08e3a-bc03-4416-ab85-120b4bf5a46b",
    "s3_url": "https://jataware-world-modelers.s3.amazonaws.com/dojo/shorthand_templates/40f08e3a-bc03-4416-ab85-120b4bf5a46b/26e184b8b8a861c26e703e4bdfaeef0a.template.txt",
    "path": "/home/clouseau/twist-global-model/main/run_TWIST.py"
  }
resp = requests.post(f"{url}/dojo/config", json=[config])
print(resp.text)


#### Add OutputFile
outputfile = json.loads(open("twist_output.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)