#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("chirps.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/897da460-6118-4a13-9d41-38e948792cb9/b5cf7b98244467a0336cbd360f3ca7f0.template.txt",
    "model_id": "897da460-6118-4a13-9d41-38e948792cb9",
    "command": "python3 run_chirps_tiff.py --name=CHIRPS --month={{ month }} --year={{ year }} --bbox='[{{ left }}, {{ bottom }}, {{ right }}, {{ top }}]' --statistic={{ statistic }}",
    "output_directory": "/results"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add OutputFile 1
outputfile = json.loads(open("chirps_outputfile.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)
