from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.logger import logger
from validation import DojoSchema
from src.settings import settings

router = APIRouter()

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)

def search_by_model(model_id):
    q = {
        "query": {
            "term": {
            "model_id.keyword": {
                "value": model_id,
                "boost": 1.0
            }
            }
        }
    }
    return q    

@router.post("/dojo/directive")
def create_directive(payload: DojoSchema.ModelDirective):
    """
    Create a `directive` for a model. This is the command which is used to execute
    the model container. The `directive` is templated out using Jinja, where each templated `{{ item }}`
    maps directly to the name of a specific `parameter.
    """
    es.index(index="directives", body=payload.json(), id=payload.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/directives/{payload.id}"},
        content=f"Created directive for model with id = {payload.id}",
    )

@router.get("/dojo/directive/{model_id}")
def get_directive(model_id: str) -> DojoSchema.ModelDirective:
    results = es.search(index="directives", body=search_by_model(model_id))
    try:
        directive = results["hits"]["hits"][0]["_source"]
        return directive
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Directive for model {model_id} not found."
        )

@router.post("/dojo/config")
def create_configs(payload: List[DojoSchema.ModelConfig]):
    """
    Create one or more model `configs`. A `config` is a settings file which is used by the model to 
    set a specific parameter level. Each `config` is stored to S3, templated out using Jinja, where each templated `{{ item }}`
    maps directly to the name of a specific `parameter.
    """    
    for p in payload:
        es.index(index="configs", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/config/{p.id}"},
        content=f"Created config(s) for model with id = {p.model_id}",
    )

@router.get("/dojo/config/{model_id}")
def get_configs(model_id: str) -> List[DojoSchema.ModelConfig]:
    results = es.search(index="configs", body=search_by_model(model_id))
    try:
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Config(s) for model {model_id} not found."
        )    

@router.post("/dojo/outputfile")
def create_outputfiles(payload: List[DojoSchema.ModelOutputFile]):
    """
    Create an `outputfile` for a model. Each `outputfile` represents a single file that is created upon each model
    execution. Here we store key metadata about the `outputfile` which enables us to find it within the container and 
    normalize it into a CauseMos compliant format.
    """    
    for p in payload:
        es.index(index="outputfiles", body=p.json(), id=p.id)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/api/dojo/outputfile/{p.id}"},
        content=f"Created outputfile(s) for model with id = {p.model_id}",
    )

@router.get("/dojo/outputfile/{model_id}")
def get_outputfiles(model_id: str) -> List[DojoSchema.ModelOutputFile]:
    print('sssssssssssssssssssssssssssssssssssssssssssssssss')
    results = es.search(index="outputfiles", body=search_by_model(model_id))
    try:
        print('correct', [i["_source"] for i in results["hits"]["hits"]])
        return [i["_source"] for i in results["hits"]["hits"]]
    except:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Outputfile(s) for model {model_id} not found."
        )    