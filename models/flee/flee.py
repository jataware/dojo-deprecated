#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("flee.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/ceedd3b0-f48f-43d2-b279-d74be695ed1c/fe88d30ed39ac5a9c2574701933a2bb3.template.txt",
    "model_id": "ceedd3b0-f48f-43d2-b279-d74be695ed1c",
    "command": "/bin/bash -c \"export PYTHONPATH=/home/clouseau/flee: ; bash run_flee.sh\"",
    "output_directory": "/results"
  }
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

#### Add OutputFile
outputfiles = json.loads(open("flee_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)

##### Add config
config = json.loads(open("flee_configs.json").read())
resp = requests.post(f"{url}/dojo/config", json=config)
print(resp.text)