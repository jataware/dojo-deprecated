#!/usr/bin/env python
# coding: utf-8
import requests
import json

url = "https://localhost:8000"
headers = {"Content-Type": "application/json"}

#### Create Model
payload = open("accessibility.json").read()
resp = requests.post(f"{url}/models", data=payload)
print(resp.text)

##### Add Directive
directive = {
  "id": "dojo/shorthand_templates/6c30c05d-54cd-4048-832f-0fd09793f08e/90b060c1d0eedbe1720c782e29120919.template.txt",
  "model_id": "6c30c05d-54cd-4048-832f-0fd09793f08e",
  "command": '/bin/bash -c "sudo chmod -R 777 output; set -a; source .env; luigi --module models.accessibility_model.tasks models.accessibility_model.tasks.TravelTimeToNearestDestination --country-level \'{{ country }}\' --destination {{ destination }} --trunk-road-speed-offset {{ trunk_road_speed_offset }} --primary-road-speed-offset {{ primary_road_speed_offset }} --secondary-road-speed-offset {{ secondary_road_speed_offset }} --tertiary-road-speed-offset {{ tertiary_road_speed_offset }} --unclassified-road-speed-offset {{ unclassified_road_speed_offset }} --local-scheduler"',
  "output_directory": "/results"
}
resp = requests.post(f"{url}/dojo/directive", json=directive)
print(resp.text)

#### Add OutputFiles
outputfiles = json.loads(open("accessibility_outputfiles.json").read())
resp = requests.post(f"{url}/dojo/outputfile", json=outputfiles)
print(resp.text)
