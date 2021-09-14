#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("stochastic_crop.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
    "id": "dojo/shorthand_templates/8cb140a5-4513-4ec3-af74-04277afa733b/111b31b1cca39926cc83275d94333e1c.template.txt",
    "model_id": "8cb140a5-4513-4ec3-af74-04277afa733b",
    "command": "python conflict --cfg_file ./input_files/conflict.cfg",
    "output_directory": "/results"
  }
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add config
config = json.loads(open("stochastic_crop_config.json").read())
resp = requests.post(f"{url}/dojo/config", json=config)
print(resp.text)

#### Add OutputFile
outputfiles = json.loads(open("stochastic_crop_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)

#### Add accessories
# accessories = json.loads(open("stochastic_crop_accessories.json").read())
# resp = requests.put(f"{url}/dojo/accessories", json=accessories)
# print(resp.text)

