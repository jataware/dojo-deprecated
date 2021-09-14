#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("cycles.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/923f9b79-487d-4a85-8dfa-29ab1b442829/96b146cc4134747d5654ab0d057a950e.template.txt",
    "model_id": "923f9b79-487d-4a85-8dfa-29ab1b442829",
    "command": "./cycles_dojo.py --country \"{{ country }}\" --crop-name {{ crop_name }} --start-year {{ start_year }} --end-year {{ end_year }} --start-planting-day {{ start_planting_day }} --fertilizer-rate {{ fertilizer_rate }} --weed-fraction {{ weed_fraction }}",
    "output_directory": "/results"
  }
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)


#### Add OutputFile
outputfiles = json.loads(open("cycles_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)

#### Add accessories
# accessories = json.loads(open("cycles_accessories.json").read())
# resp = requests.put(f"{url}/dojo/accessories", json=accessories)
# print(resp.text)

