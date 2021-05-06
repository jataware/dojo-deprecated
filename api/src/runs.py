from datetime import datetime
import json
import logging
import pathlib
import re
import requests
import sys
import time
from threading import Thread, current_thread
from typing import Any, Dict, Generator, List, Optional

import configparser
from elasticsearch import Elasticsearch
from jinja2 import Template

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from typing_extensions import final

from validation import RunSchema

from src.models import get_model
from src.dojo import get_directive, get_outputfiles

logger = logging.getLogger(__name__)

router = APIRouter()

config = configparser.ConfigParser()
config.read("/api/config.ini")
es = Elasticsearch(
    [config["ELASTICSEARCH"]["URL"]], port=config["ELASTICSEARCH"]["PORT"]
)

dmc_url = config["DMC"]["URL"]
dmc_port = config["DMC"]["PORT"]
dmc_user = config["DMC"]["USER"]
dmc_pass = config["DMC"]["PASSWORD"]
dmc_base_url = f"http://{dmc_url}:{dmc_port}/api/v1"

dojo_url = config["DOJO"]["URL"]

headers = {'Content-Type': 'application/json'}

@router.get("/runs")
def search_runs(query: str = Query(None)) -> List[RunSchema.RunMetadata]:
    if query:
        q = {
            "query": {
                "query_string": {
                    "query": query,
                }
            }
        }
    else:
        q = {"query": {"match_all": {}}}
    try:
        results = es.search(index="runs", body=q)
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content="No runs available."
        )

@router.get("/runs/{run_id}")
def get_run(run_id: str) -> RunSchema.RunMetadata:
    try:
        run = es.get(index="runs", id=run_id)["_source"]
    except:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return run

def dispatch_run(run):
    return

@router.post("/runs")
def create_run(run: RunSchema.RunMetadata):
    print(run)
    model = get_model(run.model_id)    

    # handle model run command
    directive = get_directive(run.model_id)
    print(directive)
    model_command = Template(directive.get('command'))
    
    # get parameters
    params = run.parameters
    param_dict = {}
    for p in params:
        param_dict[p.name] = p.value
    
    # generate command based on directive template
    model_command = model_command.render(param_dict)
    logging.info(f"Model Command is: {model_command}")

    # find output file path
    # TODO: enable handling multiple output files
    # CURRENT: only handles first output file
    outputfiles = get_outputfiles(run.model_id)
    input_file = Template(outputfiles[0]['path']).render(param_dict)
    logging.info(f"Input File is: {input_file}")

    run_conf = {
        "run_id":run.id,
        "model_image":model.get('image'),
        "model_id":model.get('id'),
        "model_command":model_command,
        "model_output_directory":directive.get('output_directory'),
        "dojo_url": dojo_url,
        "mixmasta_cmd":f"causemosify --input_file=/tmp/{input_file} --mapper=/mappers/mapper_{run.model_id}.json --geo admin3 --output_file=/tmp/{run.id}_{run.model_id}"
    }    

    payload = {
        "dag_run_id": run.id,
        "conf": run_conf
    }    

    response = requests.post(f'{dmc_base_url}/dags/model_xform/dagRuns',
                            headers=headers, 
                            auth=(dmc_user, dmc_pass),
                            json=payload)

    logging.info(f"Response from DMC: {json.dumps(response.json(), indent=4)}")
    
    run.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    es.index(index="runs", body=run.dict(), id=run.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/runs/{run.id}"},
        content=f"Created run with id = {run.id}",
    )

@router.get("/runs/{run_id}/logs")
def get_run_logs(run_id: str):
    response = requests.get(f'{dmc_base_url}/dags/model_xform/dagRuns/{run_id}/taskInstances',
                            headers=headers, 
                            auth=(dmc_user, dmc_pass))
    
    task_instances = response.json()['task_instances']
    logs = {}
    for t in task_instances:
        task_id = t['task_id']
        task_try_number = t['try_number']
        response_l = requests.get(f'{dmc_base_url}/dags/model_xform/dagRuns/{run_id}/taskInstances/{task_id}/logs/{task_try_number}',
                            headers=headers,
                            auth=(dmc_user, dmc_pass))
        logs[task_id] = response_l.text
    return Response(
        status_code=status.HTTP_200_OK,
        content=json.dumps(logs)
    )

@router.put("/runs")
def update_run(payload: RunSchema.RunMetadata):
    run_id = payload.id
    body = payload.json()
    es.index(index="runs", body=body, id=run_id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/runs/{run_id}"},
        content=f"Updated run with id = {run_id}",
    )