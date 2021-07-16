#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("google_trends.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
  "id": "dojo/shorthand_templates/ca83b434-0f6a-4375-874c-bed9032bf779/f07f739babe071f4ef8c250865d6194c.template.txt",
  "model_id": "ca83b434-0f6a-4375-874c-bed9032bf779",
  "command": "--term='{{ search_term }}' --country='{{ country }}' --admin1='{{ admin1 }}' --output=output/output.csv"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

##### Add OutputFile 1
mapper = json.loads(open("google_trends_mapper.json").read())
outputfile = {
    "id": "google_trends-outputfile-1",
    "model_id": "ca83b434-0f6a-4375-874c-bed9032bf779",
    "name": "google_trends",
    "file_type": "csv",
    "output_directory": "/output",
    "path": "output.csv",
    "transform": mapper,
}
resp = requests.post(f"{url}/dojo/outputfile", json=[outputfile])
print(resp.text)
